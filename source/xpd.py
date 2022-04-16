import requests
import utils.log as log

SOURCE_NAME = "xpd"


def get_source(source):
    tracking_id = source["tracking_id"]
    url = "http://gzdgj.kingtrans.net/WebTrack"

    s = requests.session()

    querystring = {"action":"list"}
    payload = "language=zh&istrack=false&Submit=%E6%9F%A5%E8%AF%A2&bills=" + tracking_id
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        }

    r = s.request("POST", url, data=payload, headers=headers, params=querystring)

    querystring = {"action":"repeat"}
    payload = "index=0&isRepeat=no&language=zh&billid=" + tracking_id
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        }

    r = s.request("POST", url, data=payload, headers=headers, params=querystring)

    return r.text.split("\n",1)[1]