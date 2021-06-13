from setuptools import find_packages, setup

setup(
    name="leet2git",
    version="0.1.0",
    packages=find_packages("scripts"),
    package_dir={"": "scripts"},
    package_data={"leet2git": ["py.typed"]},
    install_requires=[
        "appdirs == 1.4.4",
        "autoimport == 0.7.0",
        "bs4 == 0.0.1",
        "browser-cookie3 == 0.12.1",
        "click == 8.0.1",
        "requests == 2.25.1",
        "black == 21.5b2",
        "isort == 5.6.4",
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