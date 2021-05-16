def get_tags():
    import json

    import browser_cookie3
    import requests

    url = "https://leetcode.com/profile/"
    client = requests.session()
    r = client.get(url, cookies=browser_cookie3.chrome())
    cookies = r.request.headers["Cookie"]
    csrftoken = client.cookies["csrftoken"]

    url = "https://leetcode.com/graphql"

    payload = json.dumps(
        {
            "operationName": "questionData",
            "variables": {"titleSlug": "maximum-building-height"},
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

    print(json.loads(response.text)["data"]["question"]["topicTags"])
