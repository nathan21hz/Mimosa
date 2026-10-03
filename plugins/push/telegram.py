import requests
import json

from mimosa.utils.template import render

def do_push(push_config, data):
    bot_token = push_config["bot_token"]
    to = str(push_config["to"])
    msg_text = render(push_config["text"], data)
    a = requests.get("https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}".format(
        bot_token, 
        to,
        msg_text
    ), timeout=10)
    if a.json()["ok"] == True:
        return True, "OK"
    else:
        return False, "Status {}".format(a.json()["description"])