import platform
import sys

__version__ = "0.0.2"


def version_info() -> str:
    """Display the version of the program, python and the platform."""
    info = {
        "leet2git version": __version__,
        "python version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
    }
    return "\n".join(f"{k + ':' :>30} {v}" for k, v in info.items())
