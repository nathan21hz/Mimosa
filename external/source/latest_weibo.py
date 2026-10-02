import requests
import json

SOURCE_NAME = "latest_weibo"

def get_source(source):
    url = "https://api.weibo.com/2/statuses/home_timeline.json"
    access_token = source["access_token"]
    querystring = {
        "access_token":access_token,
        "count":"100"
    }
    response = requests.get(url, params=querystring, timeout=10)
    user_id = int(source["user_id"])
    for status in response.json()["statuses"]:
        if status["user"]["id"] == user_id:
            return json.dumps(status)