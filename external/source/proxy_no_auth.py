import requests
import logging

logger = logging.getLogger(__name__)

SOURCE_NAME = "proxy_no_auth"

headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36"
}

def get_source(source):
    method = source["method"]
    if "*url" in source:
        url = source["*url"]
    else:
        url = source["url"]

    cookies = source.get("cookies",{})
    proxies = source.get("proxies",{})
    custom_headers = source.get("headers",{})
    timeout = source.get("timeout", 10)
    headers.update(custom_headers)
    if method == "GET":
        r = requests.get(url, headers=headers, timeout=timeout, cookies=cookies, proxies=proxies)
        if source.get("encoding"):
            r.encoding = source["encoding"]
        return r.text
    elif method == "POST":
        r = requests.post(url, headers=headers, data=source["payload"], timeout=timeout, cookies=cookies, proxies=proxies)
        if source.get("encoding"):
            r.encoding = source["encoding"]
        return r.text
    else:
        logger.error("Method error.")
        return ""