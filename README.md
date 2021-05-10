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

For windows users, unzipping might not work because of firewall.

In that case, just download and unzip the [file](https://github.com/skygragon/leetcode-cli/releases/download/2.6.2/leetcode-cli.node10.win32.x64.zip) into bin/dist folder.

### Login to Leetcode

Currently, the only way to login is logging into chrome/firefox, then running:

```shell
$ make leetcode-login
```

This command automatically gets the needed cookies from the browser.

### Downloading a Question

To generate the files of a given question:

```shell
$ make get-question ID=<question_id>
```

## Question Solutions

| ID | Problem    | Category | Difficulty | From |
|:--:|------------|----------|------------|------|
