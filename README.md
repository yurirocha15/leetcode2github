# leetcode-practice-python

Gets a question information and generates the python file and the test file, and updates a table in the README.

Uses [leetcode-cli](https://github.com/skygragon/leetcode-cli) to get the question information.

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