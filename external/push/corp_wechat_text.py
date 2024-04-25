import requests
import json

def do_push(push_config, data):
    push_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=" + push_config["key"]
    push_payload = {
        "msgtype": "text",
        "text": {
            "content": push_config["text"].format(*data)
        }
    }
    a = requests.post(push_url,data=json.dumps(push_payload),timeout=10)
    if a.json()["errcode"] == 0:
        return True, "OK"
    else:
        return False, "Status {}".format(a.json()["errmsg"])