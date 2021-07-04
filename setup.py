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
    install_requires=[
        "appdirs == 1.4.4",
        "autoimport == 0.7.0",
        "beautifulsoup4 == 4.9.3",
        "browser-cookie3 == 0.12.1",
        "click == 8.0.1",
        "black == 21.5b2",
        "isort == 5.6.4",
        "GitPython == 3.1.18",
        "requests == 2.25.1",
    ],
    extra_require={
        "dev": [
            "flake8 == 3.8.4",
            "flake8-bugbear == 20.11.1",
            "flake8-builtins == 1.5.3",
            "flake8-polyfill == 1.0.2",
            "flake8-pytest == 1.3",
            "flake8-use-fstring == 1.1",
            "mypy == 0.790",
            "mypy-extensions == 0.4.3",
            "pep8-naming == 0.11.1",
            "pre-commit == 2.9.2",
            "pycodestyle == 2.6.0",
            "pyflakes == 2.2.0",
            "pytest == 6.1.2",
            "pytest-cov == 2.10.1",
            "pytest-custom-exit-code == 0.3.0",
            "pytest-flake8 == 1.0.6",
            "pytest-mypy == 0.8.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "leet2git = leet2git.leet2git:leet2git",
        ],
    },
)
