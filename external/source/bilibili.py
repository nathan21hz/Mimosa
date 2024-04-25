import utils.log as log
from functools import reduce
from hashlib import md5
import urllib.parse
import time
import requests
import json
import random

SOURCE_NAME = "bilibili"

headers = {
    # "Cookie": "buvid3=D1556958-B0B0-152D-B1F1-C5841EBD071826681infoc;",
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36"
}

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def getMixinKey(orig: str):
    '对 imgKey 和 subKey 进行字符顺序打乱编码'
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    '为请求参数进行 wbi 签名'
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time                                   # 添加 wts 字段
    params = dict(sorted(params.items()))                       # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v 
        in params.items()
    }
    query = urllib.parse.urlencode(params)                      # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()    # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params

def getWbiKeys() -> tuple[str, str]:
    '获取最新的 img_key 和 sub_key'
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers, timeout=10)
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

def get_source(source):
    session = requests.Session()
    BILI_VIDEO_API = "https://api.bilibili.com/x/space/wbi/arc/search"
    mid = source["mid"]
    headers["Referer"] = "https://space.bilibili.com/"+mid
    session.get("https://space.bilibili.com/"+mid, headers=headers, timeout=10)
    img_key, sub_key = getWbiKeys()
    
    dm_rand = 'ABCDEFGHIJK'
    dm_img_list = '[]'
    dm_img_str = ''.join(random.sample(dm_rand, 2))
    dm_cover_img_str = ''.join(random.sample(dm_rand, 2))
    dm_img_inter = '{"ds":[],"wh":[0,0,0],"of":[0,0,0]}'

    signed_params = encWbi(
        params={
            'mid': mid,
            "dm_img_list": dm_img_list,
            "dm_img_str": dm_img_str,
            "dm_cover_img_str": dm_cover_img_str,
            "dm_img_inter": dm_img_inter
            # "dm_img_list":"[]",
            # "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
            # "dm_img_inter": '{"ds":[],"wh":[0,0,0],"of":[0,0,0]}',
            # "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDIwNjAgU1VQRVIgKDB4MDAwMDFGMDYpIERpcmVjdDNEMTEgdnNfNV8wIHBzXzVfMCwgRDNEMTEpR29vZ2xlIEluYy4gKE5WSURJQS"
        },
        img_key=img_key,
        sub_key=sub_key
    )
    query = urllib.parse.urlencode(signed_params)
    
    cookie_req = session.get("https://api.bilibili.com/x/frontend/finger/spi", headers=headers)
    cookies = {
        "buvid3": cookie_req.json()["data"]["b_3"],
    }
    
    url = BILI_VIDEO_API + "?" + query
    resp = session.get(url, headers=headers, cookies=cookies)
    json_content = resp.json()
    # print(json_content)
    return json.dumps(json_content["data"]["list"]["vlist"][0])