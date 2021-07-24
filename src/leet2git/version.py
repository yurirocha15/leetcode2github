import os
import platform
import re
import sys

__version__ = "0.14.0"


def version_info() -> str:
    """Display the version of the program, python and the platform."""
    info = {
        "leet2git version": __version__,
        "python version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
    }
    return "\n".join(f"{k + ':' :>30} {v}" for k, v in info.items())


def update_version_string(new_version: str):
    """Updates the version string

    Args:
        new_version (str): the new version
    """
    # remove trailing v
    if new_version and new_version[0] == "v":
        new_version = new_version[1:]

    if not re.match(r"^(\d+\.)?(\d+\.)?(\d+)$", new_version):
        print(f"Version {new_version} is not valid")
        return

    file_path = os.path.abspath(__file__)
    version_regex = re.compile(r"(^_*?version_*?\s*=\s*['\"])(\d+\.\d+\.\d+)", re.M)
    with open(file_path, "r+") as f:
        content = f.read()
        f.seek(0)
        f.write(
            re.sub(
                version_regex,
                lambda match: "{}{}".format(match.group(1), new_version),
                content,
            )
        )
        f.truncate()


if __name__ == "__main__":
    update_version_string(sys.argv[1])
