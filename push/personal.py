import requests
import json

def do_push(push_config, data):
    push_payload = {
        "title":push_config["title"],
        "text":"测试{}".format(data[0]),
        "type":push_config["push_type"],
        "to":str(push_config["to"]),
        "token":push_config["token"]
    }
    a = requests.post(push_config["url"],data=json.dumps(push_payload))
    if a.json()["state"] == 0:
        return True, "OK"
    else:
        return False, "Status {}".format(a.json()["state"])