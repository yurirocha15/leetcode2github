import os
import time
from multiprocessing import Process
from multiprocessing.managers import SyncManager
from typing import Dict

import click
from click.exceptions import Abort
from leet2git.config_manager import ConfigManager
from leet2git.file_handler import FileHandler, generate_files
from leet2git.leetcode_client import LeetcodeClient
from leet2git.my_utils import mgr_init, reset_config
from leet2git.question_db import QuestionData, QuestionDB
from leet2git.readme_handler import ReadmeHandler


@click.group()
def leet2git():
    pass


@leet2git.command()
@click.argument("id", type=int)
def get_question(id: int):
    """Generates all the files for a question

    Args:
        id (int): the question id
    """
    cm = ConfigManager()
    config = cm.get_config()
    lc = LeetcodeClient()
    qdb = QuestionDB(config)
    qdb.load()

    if qdb.check_if_exists(id):
        click.secho("Question already imported")
        return

    if not qdb.check_if_slug_is_known(id):
        qdb.set_id_title_map(lc.get_id_title_map())
        qdb.save()

    # get question data
    args: Dict[int, QuestionData] = {}
    generate_files(args, id, qdb.get_title_from_id(id), lc, time.time(), config["language"])

    if id in args:
        # store data
        qdb.add_question(args[id])
        qdb.save()

        # update readme
        rh = ReadmeHandler(config)
        rh.build_readme(qdb.get_sorted_list(sort_by="creation_time"))


@leet2git.command()
@click.argument("id", type=int)
def submit_question(id: int):
    """Submit a question to Leetcode

    Args:
        id (int): the question id
    """
    cm = ConfigManager()
    config = cm.get_config()
    # submissions
    qdb = QuestionDB(config)
    qdb.load()
    problems = qdb.get_data()
    # create submit file
    if qdb.check_if_exists(id):
        file_handler = FileHandler(qdb.get_question(id), config["language"])
        code = file_handler.generate_submission_file()

        lc = LeetcodeClient()
        try:
            lc.submit_question(code, qdb.get_question(id).internal_id, config["language"])
        except Exception as e:
            click.secho(e.args, fg="red")
    else:
        click.secho(f"Could not find the question with id {id}")


@leet2git.command()
def get_all_submissions():
    """Get all solutions and generate their files"""
    cm = ConfigManager()
    config = cm.get_config()
    lc = LeetcodeClient()
    qdb = QuestionDB(config)
    qdb.load()
    has_next: bool = True
    last_key: str = ""
    offset: int = 0
    imported_cnt = 0

    try:
        while has_next:
            jobs = []
            manager = SyncManager()
            manager.start(mgr_init)
            ret_dict = manager.dict()
            submissions = lc.get_submission_list(last_key, offset)
            for submission in submissions["submissions_dump"]:
                qid: int = -1
                if qdb.check_if_id_is_known(submission["title_slug"]):
                    qid = qdb.get_id_from_title(submission["title_slug"])
                else:
                    qdb.set_id_title_map(lc.get_id_title_map())
                    qdb.save()
                    qid = qdb.get_id_from_title(submission["title_slug"])
                if (
                    submission["status_display"] == "Accepted"
                    and submission["lang"] == config["language"]
                    and not qdb.check_if_exists(qid)
                ):
                    if not qdb.check_if_exists(qid):
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
                                config["language"],
                                submission["code"],
                            ),
                        )
                        jobs.append(p)
                        p.start()

            for p in jobs:
                p.join()

            for data in ret_dict.values():
                qdb.add_question(data)
                imported_cnt += 1

            has_next = submissions["has_next"]
            last_key = submissions["last_key"]
            offset += 20
            qdb.save()
    except KeyboardInterrupt:
        click.secho("Stopping the process...")
        for p in jobs:
            p.join()
        for data in ret_dict.values():
            qdb.add_question(data)
            imported_cnt += 1
    except Exception as e:
        click.secho(e.args, fg="red")
    finally:
        manager.shutdown()

    qdb.save()
    # update readme
    rh = ReadmeHandler(config)
    rh.build_readme(qdb.get_sorted_list(sort_by="creation_time"))

    click.secho(f"In total, {imported_cnt} questions were imported!")


@leet2git.command()
@click.argument("id", type=int)
def remove_question(id: int):
    """Delete a question and its files

    Args:
        id (int): the question id
    """
    cm = ConfigManager()
    config = cm.get_config()
    qdb = QuestionDB(config)
    qdb.load()
    if qdb.check_if_exists(id):
        data = qdb.get_data()[id]
        try:
            os.remove(data.file_path)
            os.remove(data.test_file_path)
        except FileNotFoundError as e:
            click.secho(e.args)
        qdb.delete_question(id)
        qdb.save()
        # update readme
        rh = ReadmeHandler(config)
        rh.build_readme(qdb.get_sorted_list(sort_by="creation_time"))
        click.secho(f"The question {id} was removed.")
    else:
        click.secho(f"The question {id} could not be found!")


@leet2git.command()
@click.option(
    "--source-repository", "-s", default="", help="the path to the folder where the code will be saved"
)
@click.option("--language", "-l", default="python3", help="the default language")
def init(source_repository: str, language: str):
    """Creates a new configuration file
    \f
    Args:
        source_repository (s, optional): the path to the folder where the code will be saved. Defaults to "".
        language (l, optional): the default language. Defaults to "python3".
    """
    cm = ConfigManager()
    reset_config(cm, source_repository, language)


@leet2git.command()
@click.option(
    "--source-repository", "-s", default="", help="the path to the folder where the code will be saved"
)
@click.option("--language", "-l", default="python3", help="the default language")
def reset(source_repository: str, language: str):
    """Reset the configuration file
    \f
    Args:
        source_repository (s, optional): the path to the folder where the code will be saved. Defaults to "".
        language (l, optional): the default language. Defaults to "python3".
    """
    try:
        click.confirm("This will delete the question database. Still want to proceed?", abort=True)
    except Abort as e:
        return
    cm = ConfigManager()
    reset_config(cm, source_repository, language)
    qdb = QuestionDB(cm.get_config())
    qdb.reset()


if __name__ == "__main__":
    leet2git()