import requests
import json

def do_push(push_config, data):
    push_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=" + push_config["key"]
    title = push_config.get("title", "")
    jumpurl = push_config.get("url", "")
    picurl = push_config.get("picurl", "")

    if jumpurl or picurl:
        if jumpurl == "":
            jumpurl = " "
        if title == "":
            title = " "
        push_payload = {
            "msgtype": "news",
            "news": {
            "articles" : [
                {
                    "title" : title,
                    "description" : push_config["text"].format(*data),
                    "url" : jumpurl.format(*data),
                    "picurl" : picurl.format(*data)
                }
                ]
            }
        }
    else:
        if title != "":
            title += "\n"
        push_payload = {
            "msgtype": "text",
            "text": {
                "content": title + push_config["text"].format(*data)
            }
        }
    a = requests.post(push_url,data=json.dumps(push_payload),timeout=10)
    if a.json()["errcode"] == 0:
        return True, "OK"
    else:
        return False, "Status {}".format(a.json()["errmsg"])