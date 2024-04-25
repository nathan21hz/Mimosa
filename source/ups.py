import requests
import re
import utils.log as log

SOURCE_NAME = "ups"

headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36"
}

def get_source(source):
    a = requests.get("https://easyparcel.com/my/en/track/details/?courier=UPS&awb="+source["tracking_id"], timeout=10)
    token = re.findall(r'(?<=token : ")[0-9a-z]*', a.text)[0]
    log.debug(["Source","ups"], "Token: "+token)

    tracking_id = source["tracking_id"]
    payload = {'key': tracking_id, 'courier': '55', 'token': token}
    a = requests.post("https://easyparcel.com/my/en/?ac=doTrackStatus", data=payload, timeout=10)
    print(a.status_code)
    return a.text

