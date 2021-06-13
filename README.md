# leet2git
This repository tries to automate the steps needed to integrate your leetcode answers with github.

This includes:
 - Importing a question:
   - generates the question file,
   - generates the test file (python3 only),
   - updates the README
 - Submiting a question solution
 - Importing the latest accepted solution for each question with a single command

## Usage

Currently, it is necessary to log into leetcode on either chrome or firefox before running the commands.

### Installation

To install the needed libraries, activate a virtual environment (recommended) and run:

```shell
$ pip install -e .
```

### Init Repository

Navigate to the source repository and run:

```shell
$ leet2git init
```

### Downloading a Question

To generate the files of a given question:

```shell
$ leet2git get-question <question_id>
```

### Submitting a Question

To submit a question to leetcode:

```shell
$ leet2git submit-question <question_id>
```

### Dowloading All Submissions

To download the latest accepted submission for each solved problem:

```shell
$ leet2git get-all-submissions
```

### Removing a Question

To remove a downloaded problem (delete files and remove from readme):

```shell
$ leet2git remove-question <question_id>
```

### Reset Repository

**Warning: This will delete the current question database and cannot be undone.** Navigate to the source repository and run:

```shell
$ leet2git reset
```
