import os
import re
from typing import Tuple


def cammel_to_snake_case(func_str: str) -> Tuple[str, str]:
    ret = ""
    func_name = ""
    for i, c in enumerate(func_str):
        if c == "(":
            func_name = ret.split()[-1]
            ret += func_str[i:]
            break
        if c.isupper():
            ret += "_" + c.lower()
        else:
            ret += c
    return ret, func_name


def create_folder_if_needed(folder: str) -> None:
    if not os.path.isdir(os.path.join("src", f"{folder}_problems")):
        print(
            f"The folder {folder}_problems does not exist. Do you want to create? [y/n]"
        )
        res = input()
        if res.lower() in ["y", "yes"]:
            os.mkdir(os.path.join("src", f"{folder}_problems"))
            open(os.path.join("src", f"{folder}_problems", "__init__.py"), "a")
            with open(
                os.path.join("src", f"{folder}_problems", f"test_{folder}.py"), "a"
            ) as f:
                f.write("#!/usr/bin/env python\n")
                f.write("\n")
                f.write("import pytest\n")


def get_file_name(question: str) -> str:
    return (
        "_".join(map(lambda s: re.sub(r"[\W_]+", "", s), question.split())).lower()
        + ".py"
    )


def leetcode_cli_exists() -> bool:
    return os.path.exists(os.path.join("bin", "dist", "leetcode-cli"))


def download_leetcode_cli():
    os.system("mkdir -p bin")
    os.system(
        "wget -P bin https://github.com/skygragon/leetcode-cli/releases/download/2.6.2/leetcode-cli.node10.linux.x64.tar.gz"
    )
    os.system("tar -xvzf bin/leetcode-cli.node10.linux.x64.tar.gz -C bin")
    os.system("rm bin/leetcode-cli.node10.linux.x64.tar.gz")
