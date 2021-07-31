"""
App entry point
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""
import glob
import os
import time
import traceback
from multiprocessing import Process
from multiprocessing.managers import SyncManager
from typing import Any, Dict, List, Optional

import click
from click.core import Context
from click.exceptions import Abort

from leet2git.config_manager import ConfigManager
from leet2git.file_handler import create_file_handler, generate_files
from leet2git.leetcode_client import LeetcodeClient
from leet2git.my_utils import (
    get_question_id,
    mgr_init,
    reset_config,
    wait_to_finish_download,
)
from leet2git.question_db import QuestionData, QuestionDB
from leet2git.readme_handler import ReadmeHandler
from leet2git.version import version_info

# pylint: disable=broad-except


@click.group()
@click.version_option(version="", message=version_info())
@click.option(
    "--source-repository",
    "-s",
    default="",
    help="The path to the folder where the code will be saved. Overrides the default config",
)
@click.option(
    "--language",
    "-l",
    default="python3",
    help="The language to run the command. Overrides the default config",
)
@click.pass_context
def leet2git(
    ctx: Context,
    source_repository: Optional[str] = "",
    language: Optional[str] = "",
):
    """App entrypoint

    Args:
        ctx (Context): the context
        source_repository (str): source repository path
        language (str): the programming language
    """
    cm = ConfigManager()
    override_config = {}
    if language:
        override_config["language"] = language
    if source_repository:
        override_config["source_path"] = source_repository
    cm.load_config(override_config)
    ctx.obj = cm


@leet2git.command()
@click.argument("question-id", type=int)
@click.pass_obj
def get(cm: ConfigManager, question_id: int):
    """Generates all the files for a question

    Args:
        question_id (int): the question question_id
    """
    qdb: QuestionDB = QuestionDB(cm.config)
    lc = LeetcodeClient()
    qdb.load()
    if qdb.check_if_exists(question_id):
        click.secho("Question already imported")
        return

    if not qdb.check_if_slug_is_known(question_id):
        qdb.set_id_title_map(lc.get_id_title_map())
        qdb.save()

    # get question data
    args: Dict[int, QuestionData] = {}
    generate_files(args, question_id, qdb.get_title_from_id(question_id), lc, time.time(), cm.config)

    if question_id in args:
        # store data
        qdb.add_question(args[question_id])
        qdb.save()

        # update readme
        rh = ReadmeHandler(cm.config)
        rh.build_readme(qdb.get_sorted_list(sort_by="creation_time"))


@leet2git.command()
@click.argument("question-id", type=int)
@click.pass_obj
def submit(cm: ConfigManager, question_id: int):
    """Submit a question to Leetcode

    Args:
        question_id (int): the question question_id
    """
    qdb: QuestionDB = QuestionDB(cm.config)
    qdb.load()
    # create submit file
    if qdb.check_if_exists(question_id):
        file_handler = create_file_handler(qdb.get_question(question_id), cm.config)
        code = file_handler.generate_submission_file()

        lc = LeetcodeClient()
        try:
            lc.submit_question(code, qdb.get_question(question_id).internal_id, cm.config["language"])
        except Exception as e:
            click.secho(e.args, fg="red")
            click.secho(traceback.format_exc())
    else:
        click.secho(f"Could not find the question with id {question_id}")


@leet2git.command()
@click.pass_obj
def import_all(cm: ConfigManager):
    """Get all solutions and generate their files"""
    qdb: QuestionDB = QuestionDB(cm.config)
    lc = LeetcodeClient()
    qdb.load()
    has_next: bool = True
    last_key: str = ""
    offset: int = 0
    imported_cnt = 0

    try:
        while has_next:
            jobs: List[Process] = []
            manager = SyncManager()
            manager.start(mgr_init)
            ret_dict: Dict[Any, Any] = manager.dict()
            submissions = lc.get_submission_list(last_key, offset)
            if "submissions_dump" not in submissions:
                if imported_cnt <= 0:
                    raise ValueError(
                        "No submission to import. Are you logged in to leetcode? (Chrome or Firefox)"
                    )
                break
            for submission in submissions["submissions_dump"]:
                qid: int = get_question_id(submission["title_slug"], qdb, lc)
                if (
                    submission["status_display"] == "Accepted"
                    and submission["lang"] == cm.config["language"]
                    and not qdb.check_if_exists(qid)
                ):
                    # pre-store the question
                    data = QuestionData(id=qid)
                    qdb.add_question(data)
                    p = Process(
                        target=generate_files,
                        args=(
                            ret_dict,
                            qid,
                            submission["title_slug"],
                            lc,
                            submission["timestamp"],
                            cm.config,
                            submission["code"],
                        ),
                    )
                    jobs.append(p)
                    p.start()

            imported_cnt += wait_to_finish_download(jobs, ret_dict, qdb)

            has_next = submissions["has_next"]
            last_key = submissions["last_key"]
            offset += 20
            qdb.save()
    except KeyboardInterrupt:
        click.secho("Stopping the process...")
        imported_cnt += wait_to_finish_download(jobs, ret_dict, qdb)
    except Exception as e:
        click.secho(e.args, fg="red")
        click.secho(traceback.format_exc())
    finally:
        manager.shutdown()

    qdb.save()
    # update readme
    rh = ReadmeHandler(cm.config)
    rh.build_readme(qdb.get_sorted_list(sort_by="creation_time"))

    click.secho(f"In total, {imported_cnt} questions were imported!")


@leet2git.command()
@click.argument("question-id", type=int)
@click.pass_obj
def delete(cm: ConfigManager, question_id: int):
    """Delete a question and its files

    Args:
        question_id (int): the question question_id
    """
    qdb: QuestionDB = QuestionDB(cm.config)
    qdb.load()
    if qdb.check_if_exists(question_id):
        data = qdb.get_data()[question_id]
        try:
            os.remove(data.file_path)
            os.remove(data.test_file_path)
        except FileNotFoundError as e:
            click.secho(e.args)
        qdb.delete_question(question_id)
        qdb.save()
        # update readme
        rh = ReadmeHandler(cm.config)
        rh.build_readme(qdb.get_sorted_list(sort_by="creation_time"))
        click.secho(f"The question {question_id} was removed.")
    else:
        click.secho(f"The question {question_id} could not be found!")


@leet2git.command()
@click.option(
    "--source-repository", "-s", default="", help="the path to the folder where the code will be saved"
)
@click.option("--language", "-l", default="python3", help="the default language")
@click.option("--create-repo", "-c", is_flag=True, help="generates a git repository")
@click.pass_obj
def init(cm: ConfigManager, source_repository: str, language: str, create_repo: bool):
    """Creates a new configuration file and can generate a git repository.
    \f
    Args:
        source_repository (str, optional): the path to the folder where the code will be saved.
            Defaults to "".
        language (str, optional): the default language. Defaults to "python3".
        create_repo (bool, optional): generates a git repository. Defaults to False.
    """
    reset_config(cm, source_repository, language, load_old=False)
    cm.load_config()
    if create_repo:
        data = QuestionData(language=cm.config["language"])
        file_handler = create_file_handler(data, cm.config)
        file_handler.generate_repo(cm.config["source_path"])


@leet2git.command()
@click.option(
    "--source-repository", "-s", default="", help="the path to the folder where the code will be saved"
)
@click.option("--language", "-l", default="python3", help="the default language")
@click.option(
    "--soft/--hard",
    default=True,
    help="A soft reset only erases the database. A hard reset also erase the files.",
)
@click.pass_obj
def reset(cm: ConfigManager, source_repository: str, language: str, soft: bool):
    """Reset the configuration file
    \f
    Args:
        source_repository (str, optional): the path to the folder where the code will be saved.
            Defaults to "".
        language (str, optional): the default language. Defaults to "python3".
        soft(bool, optional): the reset hardness. Defaults to soft.
    """
    if not soft:
        try:
            click.confirm(
                f"This will delete EVERY solution and test file inside \
                    the {cm.config['source_path']} folder. \
                     Still want to proceed?",
                abort=True,
            )
        except Abort:
            return

        file_list = glob.glob(os.path.join(cm.config["source_path"], "src", "leetcode_*")) + glob.glob(
            os.path.join(cm.config["source_path"], "tests", "test_*")
        )

        for file in file_list:
            try:
                os.remove(file)
            except FileNotFoundError as e:
                click.secho(e.args)

    else:
        try:
            click.confirm("This will delete the question database. Still want to proceed?", abort=True)
        except Abort:
            return

    reset_config(cm, source_repository, language)
    cm.load_config()
    qdb = QuestionDB(cm.config)
    qdb.reset()

    if not soft:
        data = QuestionData(language=cm.config["language"])
        file_handler = create_file_handler(data, cm.config)
        file_handler.generate_repo(cm.config["source_path"])


if __name__ == "__main__":
    leet2git()  # pylint: disable=no-value-for-parameter
