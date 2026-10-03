import requests
import json

from mimosa.utils.template import render

def do_push(push_config, data):
    push_payload = {
        "title":push_config["title"],
        "text":render(push_config["text"], data),
        "type":push_config["push_type"],
        "to":str(push_config["to"]),
        "token":push_config["token"]
    }
    a = requests.post(push_config["url"],data=json.dumps(push_payload),timeout=10)
    if a.json()["state"] == 0:
        return True, "OK"
    else:
        return False, "Status {}".format(a.json()["state"])