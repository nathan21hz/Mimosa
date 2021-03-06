import requests
import json

def do_push(push_config, data):
    push_payload = {
        "title":push_config["title"],
        "text":push_config["text"].format(*data),
        "type":push_config["push_type"],
        "to":str(push_config["to"]),
        "token":push_config["token"]
    }
    a = requests.post(push_config["url"],data=json.dumps(push_payload),timeout=10)
    if a.json()["state"] == 0:
        return True, "OK"
    else:
        return False, "Status {}".format(a.json()["state"])