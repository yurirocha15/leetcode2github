import json
import os
import re
import time

import browser_cookie3
import requests
from question_db import QuestionData, QuestionDB


class LeetcodeClient:
    def __init__(self):
        self.binary_path = os.path.join("bin", "dist", "leetcode-cli")

    def login(self):
        os.system(self.binary_path + " user -c")

    def logout(self):
        os.system(self.binary_path + " user -L")

    def get_question_data(self, id) -> QuestionData:
        data = QuestionData(id=id, creation_time=time.time())
        os.system(
            self.binary_path + " show " + str(id) + " -gx -l python3 -o ./src > tmp.txt"
        )
        with open("tmp.txt", "r", encoding="UTF8") as f:
            for i, line in enumerate(f):
                print(line)
                if i == 0:
                    data.title = " ".join(line.split()[1:])
                elif "Source Code:" in line:
                    data.file_path = line.split()[3]
                elif "https://leetcode" in line:
                    data.url = line[:-1]
                elif "Input: " in line:
                    data.inputs.append(line[7:-1].replace("null", "None"))
                elif "Output: " in line:
                    data.outputs.append(line[8:-1].replace("null", "None"))
                elif line[0] == "*":
                    words = line.split()
                    if words[1] in ["Easy", "Medium", "Hard"]:
                        data.difficulty = words[1]

        os.remove("tmp.txt")
        new_file_path = (
            data.file_path.replace(".", "-", 1)
            .replace("/", "/leetcode-", 1)
            .replace("-", "_")
        )
        os.rename(data.file_path, new_file_path)
        data.file_path = new_file_path
        with open(data.file_path, "r") as f:
            text = f.read()
            data.function_name = re.findall(r"    def (.*?)\(self,", text)[0]

        data.categories = self.get_tags(data.url.split("/")[-3])

        return data

    def get_tags(self, question_name):
        url = "https://leetcode.com/profile/"
        client = requests.session()
        r = client.get(url, cookies=browser_cookie3.chrome())
        cookies = r.request.headers["Cookie"]
        csrftoken = client.cookies["csrftoken"]

        url = "https://leetcode.com/graphql"

        payload = json.dumps(
            {
                "operationName": "questionData",
                "variables": {"titleSlug": question_name},
                "query": "query questionData($titleSlug: String) {\n  question(titleSlug: $titleSlug) {\n    questionId\n    questionFrontendId\n    boundTopicId\n    title\n    titleSlug\n    content\n    translatedTitle\n    translatedContent\n    isPaidOnly\n    difficulty\n    likes\n    dislikes\n    isLiked\n    similarQuestions\n    exampleTestcases\n    contributors {\n      username\n      profileUrl\n      avatarUrl\n      __typename\n    }\n    topicTags {\n      name\n      slug\n      translatedName\n      __typename\n    }\n    companyTagStats\n    codeSnippets {\n      lang\n      langSlug\n      code\n      __typename\n    }\n    stats\n    hints\n    solution {\n      id\n      canSeeDetail\n      paidOnly\n      hasVideoSolution\n      paidOnlyVideo\n      __typename\n    }\n    status\n    sampleTestCase\n    metaData\n    judgerAvailable\n    judgeType\n    mysqlSchemas\n    enableRunCode\n    enableTestMode\n    enableDebugger\n    envInfo\n    libraryUrl\n    adminUrl\n    __typename\n  }\n}\n",
            }
        )
        headers = {
            "authority": "leetcode.com",
            "pragma": "no-cache",
            "cache-control": "no-cache",
            "dnt": "1",
            "sec-ch-ua-mobile": "?0",
            "content-type": "application/json",
            "accept": "*/*",
            "origin": "https://leetcode.com",
            "cookie": cookies,
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        return json.loads(response.text)["data"]["question"]["topicTags"]

    def get_leetcode_cookies(self):
        url = "https://leetcode.com/profile/"
        leetcode_session = ""
        csrftoken = ""
        username = ""
        try:
            browsers = (browser_cookie3.chrome(), browser_cookie3.firefox())
        except browser_cookie3.BrowserCookieError as e:
            print(e.args)

        for browser in browsers:
            try:
                client = requests.session()
                r = client.get(url, cookies=browser)
                cookies = r.request.headers["Cookie"]
                csrftoken = client.cookies["csrftoken"]
            except:
                continue
            leetcode_session = re.findall(
                r"LEETCODE_SESSION=(.*?);|$", cookies, flags=re.DOTALL
            )[0]
            username = re.findall(r"username: '(.*?)',", r.text, flags=re.DOTALL)[0]
            if leetcode_session and csrftoken and username:
                break

        if not leetcode_session or not csrftoken or not username:
            raise ValueError(
                "ERROR: Could not find the cookies neither on Chrome nor Firefox."
                + " Make sure to login to leetcode in one of these browsers."
            )

        return username, leetcode_session, csrftoken


if __name__ == "__main__":
    lc = LeetcodeClient()
    print(lc.get_question_data(1848))
