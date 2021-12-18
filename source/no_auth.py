import requests
import utils.log as log

SOURCE_NAME = "no_auth"

headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36"
}

def get_source(source):
    method = source["method"]
    if "*url" in source:
        url = source["*url"]
    else:
        url = source["url"]
    if method == "GET":
        r = requests.get(url, headers=headers)
        return r.text
    elif method == "POST":
        r = requests.post(url, headers=headers, data=source["payload"], timeout=10)
        return r.text
    else:
        log.error(["Source","no_auth"], "Method error.")
        return ""