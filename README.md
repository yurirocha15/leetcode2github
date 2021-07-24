# leet2git
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-2-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
This repository tries to automate the steps needed to integrate your leetcode answers with github.

This includes:
 - Importing a question:
   - generates the question file,
   - generates the test file (python3 only),
   - updates the README
 - Submiting a question solution
 - Importing the latest accepted solution for each question with a single command

## Installation

To install the needed libraries, activate a virtual environment (recommended) and run:

```shell
$ pip install leet2git
```

### Install from Source

To install from source, download this repository, navigate to the folder and run:

```shell
$ pip install -e .[dev]
```

## Usage

Currently, it is necessary to log into leetcode on either chrome or firefox before running the commands.

```shell
$ leet2git --help
Usage: leet2git [OPTIONS] COMMAND [ARGS]...

Options:
  --version                     Show the version and exit.
  -s, --source-repository TEXT  The path to the folder where the code will be saved. Overrides the default config
  -l, --language TEXT           The language to run the command. Overrides the default config
  --help                        Show this message and exit.

Commands:
  delete      Delete a question and its files
  get         Generates all the files for a question
  import-all  Get all solutions and generate their files
  init        Creates a new configuration file and can generate a git repository.
  reset       Reset the configuration file
  submit      Submit a question to Leetcode
```

### Init Repository

Navigate to the source repository and run:

```shell
$ leet2git init --help
Usage: leet2git init [OPTIONS]

  Creates a new configuration file and can generate a git repository.

Options:
  -s, --source-repository TEXT  the path to the folder where the code will be saved
  -l, --language TEXT           the default language
  -c, --create-repo             generates a git repository
```

Running this command will open the configuration file in the default editor.

### Dowloading All Submissions

To download the latest accepted submission for each solved problem:

```shell
$ leet2git import-all
```

### Downloading a Question to Solve

To generate the files of a given question:

```shell
$ leet2git get --help
Usage: leet2git get [OPTIONS] ID

  Generates all the files for a question

  Args:     id (int): the question id
```

### Submitting a Question

To submit a question to leetcode:

```shell
$ leet2git submit --help
Usage: leet2git submit [OPTIONS] ID

  Submit a question to Leetcode

  Args:     id (int): the question id
```

### Removing a Question

To remove a downloaded problem (delete files and remove from readme):

```shell
$ leet2git delete --help
Usage: leet2git delete [OPTIONS] ID

  Delete a question and its files

  Args:     id (int): the question id
```

### Reset Repository

**Warning: This will delete the current question database and cannot be undone.** Navigate to the source repository and run:

```shell
$ leet2git reset --help
Usage: leet2git reset [OPTIONS]

  Reset the configuration file

Options:
  -s, --source-repository TEXT  the path to the folder where the code will be saved
  -l, --language TEXT           the default language
  --soft (default) / --hard               A soft reset only erases the database. A hard reset also erase the files.
```

Running this command will open the configuration file in the default editor.

## Configuration

Running either the init or the reset command will open the configuration file in the default editor.
The file location will also be printed in the terminal, so you can edit in manually later.

### Example Configuration

```json
{
    "language": "python3",
    "source_path": "path_to_repository",
    "readme": {
        "show_difficulty": true,
        "show_category": true
    },
    "source_code": {
        "add_description": true
    },
    "test_code": {
        "generate_tests": true
    }
}
```

### language

The default language the Download/Submit the questions. Can be overriden when running a command with the -l option.

Available Options:
- "bash"
- "c"
- "cpp"
- "csharp"
- "golang"
- "java"
- "javascript"
- "kotlin"
- "mysql"
- "php"
- "python"
- "python3"
- "ruby"
- "rust"
- "scala"
- "swift"

### source_path

The path to the code repository

### readme

- show_difficulty: If true, will generate an extra section on README with different tables for each difficulty.
- show_category: If true, will generate an extra section on README with different tables for each category.

### source_code

- add_description: If True, will add the problem description as comments in the source file.

### test_code

- generate_tests: If true, will try to generate local test files for the question. Currently only python3 is supported.


## Language Support

| Language | Generate/Import Question | Generate Local Tests | Submit Question | Auto Import/Include Libraries |
|:--------:|--------------------------|----------------------|-----------------|-------------------------------|
| bash | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| c | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| cpp | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| csharp | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| golang | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| java | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| javascript | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| kotlin | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| mysql | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| php | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| python | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| python3 | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :large_orange_diamond: |
| ruby | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| rust | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| scala | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |
| swift | :heavy_check_mark: | :x: | :heavy_check_mark: | :x: |

:heavy_check_mark:: Fully Supported
:large_orange_diamond:: Partially Supported
:x:: Not Supported

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://www.yurirocha.com"><img src="https://avatars.githubusercontent.com/u/4281771?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Yuri Rocha</b></sub></a><br /><a href="https://github.com/yurirocha15/leetcode2github/commits?author=yurirocha15" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/sungho-joo"><img src="https://avatars.githubusercontent.com/u/53804787?v=4?s=100" width="100px;" alt=""/><br /><sub><b>sungho-joo</b></sub></a><br /><a href="https://github.com/yurirocha15/leetcode2github/commits?author=sungho-joo" title="Code">💻</a> <a href="https://github.com/yurirocha15/leetcode2github/issues?q=author%3Asungho-joo" title="Bug reports">🐛</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!