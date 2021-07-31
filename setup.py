import io
import os
import re
from glob import glob

from setuptools import find_packages, setup

with open("src/leet2git/version.py") as file:
    version_match = re.search(r'__version__ = "(?P<version>.*)"', file.read())
    if version_match is None:
        raise ValueError("The version is not specified in the version.py file.")
    version = version_match["version"]

with open("README.md", "r") as readme_file:
    readme = readme_file.read()


def pip(filename):
    """Parse pip reqs file and transform it to setuptools requirements."""
    requirements = []
    for line in io.open(os.path.join("requirements", f"{filename}.txt")):
        line = line.strip()
        if not line or "://" in line or line.startswith("#"):
            continue
        requirements.append(line)
    return requirements


install_require = pip("requirements")
dev_require = pip("requirements-dev")

setup(
    name="leet2git",
    version=version,
    description="Tool to ease the integration between Leetcode and a Git repository",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/yurirocha15/leetcode2github",
    author="Yuri Rocha",
    author_email="yurirocha15@gmail.com",
    license="MIT License",
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={"leet2git": ["py.typed"]},
    py_modules=[os.path.splitext(os.path.basename(path))[0] for path in glob("src/leet2git/*.py")],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Utilities",
    ],
    install_requires=install_require,
    dev_require=dev_require,
    extras_require={
        "dev": dev_require,
    },
    entry_points={
        "console_scripts": [
            "leet2git = leet2git.leet2git:leet2git",
        ],
    },
)
