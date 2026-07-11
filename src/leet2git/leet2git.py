"""
App entry point
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import glob
import os
import time
from collections.abc import Mapping
from multiprocessing import Process
from multiprocessing.managers import SyncManager

import click
from click.core import Context
from click.exceptions import Abort

from leet2git.cli_helpers import (
    get_question_id,
    mgr_init,
    reset_config,
    wait_to_finish_download,
)
from leet2git.config_manager import ConfigManager, ConfigOverrides
from leet2git.file_handler import create_file_handler, generate_files
from leet2git.leetcode_client import LeetcodeAPIError, LeetcodeAuthError, LeetcodeClient
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
    source_repository: str = "",
    language: str = "",
) -> None:
    """Leet2Git App
    \f
    Args:
        ctx (Context): the context
        source_repository (str): source repository path
        language (str): the programming language
    """
    cm = ConfigManager()
    override_config = ConfigOverrides()
    if language:
        override_config.language = language
    if source_repository:
        override_config.source_path = source_repository
    cm.load_config(override_config)
    ctx.obj = cm


@leet2git.command()
@click.argument("question-id", type=int)
@click.pass_obj
def get(cm: ConfigManager, question_id: int) -> None:
    """Generates all the files for a question

    Args:
        question_id (int): the question question_id
    """
    qdb: QuestionDB = QuestionDB(cm.config)
    qdb.load()
    if qdb.check_if_exists(question_id):
        click.secho("Question already imported")
        return

    try:
        lc = LeetcodeClient()
        if not qdb.check_if_slug_is_known(question_id):
            qdb.set_id_title_map(lc.get_id_title_map())
            qdb.save()

        # get question data
        args: dict[int, QuestionData] = {}
        title_slug = qdb.get_title_from_id(question_id) or ""
        generate_files(args, question_id, title_slug, lc, time.time(), cm.config)
    except (LeetcodeAPIError, LeetcodeAuthError) as e:
        click.secho(str(e), fg="red")
        return

    if question_id in args:
        # store data
        qdb.add_question(args[question_id])
        qdb.save()

        # update readme
        rh = ReadmeHandler(cm.config)
        rh.build_readme(qdb.get_questions_sorted_by_creation_time())


@leet2git.command()
@click.argument("question-id", type=int)
@click.pass_obj
def submit(cm: ConfigManager, question_id: int) -> None:
    """Submit a question to Leetcode

    Args:
        question_id (int): the question question_id
    """
    qdb: QuestionDB = QuestionDB(cm.config)
    qdb.load()
    # create submit file
    question_data = qdb.get_question(question_id)
    if not question_data:
        click.secho(f"Could not find the question with id {question_id}")
        return

    file_handler = create_file_handler(question_data, cm.config)
    code = file_handler.generate_submission_file()

    try:
        lc = LeetcodeClient()
        title_slug = question_data.title_slug or qdb.get_title_from_id(question_id) or ""
        lc.submit_question(code, question_data.internal_id, title_slug, cm.config.language)
    except (LeetcodeAPIError, LeetcodeAuthError) as e:
        click.secho(str(e), fg="red")


@leet2git.command()
@click.argument("question-id", type=int)
@click.pass_obj
def run(cm: ConfigManager, question_id: int) -> None:
    """Run a question on Leetcode Servers

    Args:
        question_id (int): the question question_id
    """
    qdb: QuestionDB = QuestionDB(cm.config)
    qdb.load()
    # create test file
    question_data = qdb.get_question(question_id)
    if not question_data:
        click.secho(f"Could not find the question with id {question_id}")
        return

    file_handler = create_file_handler(question_data, cm.config)
    code = file_handler.generate_submission_file()

    try:
        lc = LeetcodeClient()
        title_slug = question_data.title_slug or qdb.get_title_from_id(question_id) or ""
        raw_inputs = question_data.to_wire_inputs()
        lc.submit_question(
            code,
            question_data.internal_id,
            title_slug,
            cm.config.language,
            True,
            raw_inputs,
        )
    except (LeetcodeAPIError, LeetcodeAuthError) as e:
        click.secho(str(e), fg="red")


@leet2git.command()
@click.pass_obj
def import_all(cm: ConfigManager) -> None:
    """Get all solutions and generate their files"""
    qdb: QuestionDB = QuestionDB(cm.config)
    qdb.load()
    has_next: bool = True
    last_key: str = ""
    offset: int = 0
    imported_cnt = 0
    manager: SyncManager | None = None
    jobs: list[Process] = []
    ret_dict: Mapping[object, QuestionData] | None = None

    try:
        lc = LeetcodeClient()
        while has_next:
            jobs = []
            manager = SyncManager()
            manager.start(mgr_init)
            ret_dict = manager.dict()
            submissions = lc.get_submission_list(last_key, offset)
            for submission in submissions.submissions_dump:
                qid = get_question_id(submission.title_slug, qdb, lc)
                if (
                    qid is not None
                    and submission.status_display == "Accepted"
                    and submission.lang == cm.config.language
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
                            submission.title_slug,
                            lc,
                            submission.timestamp,
                            cm.config,
                            submission.code,
                        ),
                    )
                    jobs.append(p)
                    p.start()

            imported_cnt += wait_to_finish_download(jobs, ret_dict, qdb)

            has_next = submissions.has_next
            last_key = submissions.last_key
            offset += 20
            qdb.save()
            if has_next:
                time.sleep(1)
    except KeyboardInterrupt:
        click.secho("Stopping the process...")
        if ret_dict is not None:
            imported_cnt += wait_to_finish_download(jobs, ret_dict, qdb)
    except (LeetcodeAPIError, LeetcodeAuthError, ValueError) as e:
        click.secho(str(e), fg="red")
    finally:
        if manager is not None:
            manager.shutdown()

    qdb.save()
    # update readme
    rh = ReadmeHandler(cm.config)
    rh.build_readme(qdb.get_questions_sorted_by_creation_time())

    click.secho(f"In total, {imported_cnt} questions were imported!")


@leet2git.command()
@click.argument("question-id", type=int)
@click.pass_obj
def delete(cm: ConfigManager, question_id: int) -> None:
    """Delete a question and its files

    Args:
        question_id (int): the question question_id
    """
    qdb: QuestionDB = QuestionDB(cm.config)
    qdb.load()
    if qdb.check_if_exists(question_id):
        data = qdb.get_data()[question_id]
        try:
            os.remove(os.path.join(cm.config.source_path, data.file_path))
            if data.test_file_path:
                os.remove(os.path.join(cm.config.source_path, data.test_file_path))
        except FileNotFoundError as e:
            click.secho(str(e), fg="red")
        qdb.delete_question(question_id)
        qdb.save()
        # update readme
        rh = ReadmeHandler(cm.config)
        rh.build_readme(qdb.get_questions_sorted_by_creation_time())
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
def init(cm: ConfigManager, source_repository: str, language: str, create_repo: bool) -> None:
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
        data = QuestionData(language=cm.config.language)
        file_handler = create_file_handler(data, cm.config)
        file_handler.generate_repo(cm.config.source_path)


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
def reset(cm: ConfigManager, source_repository: str, language: str, soft: bool) -> None:
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
                    the {cm.config.source_path} folder. \
                     Still want to proceed?",
                abort=True,
            )
        except Abort:
            return

        file_list = glob.glob(os.path.join(cm.config.source_path, "src", "leetcode_*")) + glob.glob(
            os.path.join(cm.config.source_path, "tests", "test_*")
        )

        for file in file_list:
            try:
                os.remove(file)
            except FileNotFoundError as e:
                click.secho(str(e), fg="red")

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
        data = QuestionData(language=cm.config.language)
        file_handler = create_file_handler(data, cm.config)
        file_handler.generate_repo(cm.config.source_path)


if __name__ == "__main__":
    leet2git()  # pylint: disable=no-value-for-parameter
