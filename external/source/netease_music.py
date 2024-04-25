import requests
import json

SOURCE_NAME = "netease_music"

headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36"
}

def get_source(source):
    NETEASE_URL = "http://music.163.com/api/artist/albums/{}?limit=5"
    uid = source["uid"]
    req = requests.get(NETEASE_URL.format(uid), headers=headers, timeout=10)
    req_json =  req.json()
    return json.dumps(req_json["hotAlbums"][0])