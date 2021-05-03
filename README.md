# leetcode-practice-python
This repository is a template which automates the boilerplate code when adding solutions to leetcode problems.

Using a single command, one can get the question information, generate the python executable template, generate the test files, and update the table at the end of the README.

This repository uses [leetcode-cli](https://github.com/skygragon/leetcode-cli) to get the question information. Big thanks to the leetcode-cli owners for providing such tool.

## Usage

### Installation

To install the needed libraries:

```shell
$ make setup
```

Currently, the only way to login is logging into chrome/firefox, then running:

```shell
$ make re-login
```

and copying the needed cookies as required.

### Downloading a Question

To generate the files of a given question:

```shell
$ make get-question ID=<question_id>
```

## Question Solutions

| ID | Problem    | Category | Difficulty | From |
|:--:|------------|----------|------------|------|
