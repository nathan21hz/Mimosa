import requests

SOURCE_NAME = "no_auth"

def get_source(source):
    method = source["method"]
    if method == "GET":
        r = requests.get(source["url"])
        return r.text
    elif method == "POST":
        r = requests.post(source["url"],data=source["payload"])
        return r.text
    else:
        print("[Source][no_auth] Meothod error")
        return ""