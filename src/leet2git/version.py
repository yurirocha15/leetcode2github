"""
Version management
Authors:
    - Yuri Rocha (yurirocha15@gmail.com)
"""

import ast
import os
import platform
import sys

import click
from pydantic import BaseModel, ValidationError, field_validator

__version__ = "0.3.1"


class VersionString(BaseModel):
    """Validated semantic version string."""

    value: str

    @field_validator("value")
    @classmethod
    def require_three_numeric_parts(cls, value: str) -> str:
        """Validate a simple MAJOR.MINOR.PATCH version."""
        version = value.removeprefix("v")
        parts = version.split(".")
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise ValueError("version must use MAJOR.MINOR.PATCH")
        return version


def version_info() -> str:
    """Display the version of the program, python and the platform."""
    info = {
        "leet2git version": __version__,
        "python version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
    }
    return "\n".join(f"{k + ':':>30} {v}" for k, v in info.items())


def update_version_string(new_version: str) -> None:
    """Updates the version string

    Args:
        new_version (str): the new version
    """
    try:
        version = VersionString(value=new_version).value
    except ValidationError:
        click.secho(f"Version {new_version} is not valid", fg="red")
        return

    file_path = os.path.abspath(__file__)
    with open(file_path, "r+") as f:
        content = f.read()
        version_line = _find_version_line(content)
        if version_line is None:
            click.secho("Could not find __version__", fg="red")
            return

        lines = content.splitlines(keepends=True)
        line_ending = "\n" if lines[version_line - 1].endswith("\n") else ""
        lines[version_line - 1] = f'__version__ = "{version}"{line_ending}'
        f.seek(0)
        f.write("".join(lines))
        f.truncate()


def _find_version_line(content: str) -> int | None:
    """Return the line where __version__ is assigned."""
    tree = ast.parse(content)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__version__":
                return node.lineno
    return None


if __name__ == "__main__":
    update_version_string(sys.argv[1])
