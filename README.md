# leet2git
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
$ pip install -e .
```

## Usage

Currently, it is necessary to log into leetcode on either chrome or firefox before running the commands.

```shell
$ leet2git --help
Usage: leet2git [OPTIONS] COMMAND [ARGS]...

Options:
  --version                     Show the version and exit.
  -s, --source-repository TEXT  The path to the folder where the code will be saved. Overrides the default config
  -l, --language TEXT           The default language. Overrides the default config
  --help                        Show this message and exit.

Commands:
  get-all-submissions  Get all solutions and generate their files
  get-question         Generates all the files for a question
  init                 Creates a new configuration file and can generate a git repository.
  remove-question      Delete a question and its files
  reset                Reset the configuration file
  submit-question      Submit a question to Leetcode
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
$ leet2git get-all-submissions
```

### Downloading a Question to Solve

To generate the files of a given question:

```shell
$ leet2git get-question --help
Usage: leet2git get-question [OPTIONS] ID

  Generates all the files for a question

  Args:     id (int): the question id
```

### Submitting a Question

To submit a question to leetcode:

```shell
$ leet2git submit-question --help
Usage: leet2git submit-question [OPTIONS] ID

  Submit a question to Leetcode

  Args:     id (int): the question id
```

### Removing a Question

To remove a downloaded problem (delete files and remove from readme):

```shell
$ leet2git remove-question --help
Usage: leet2git remove-question [OPTIONS] ID

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
