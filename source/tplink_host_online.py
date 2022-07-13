import requests
import json
import urllib.parse
# import utils.log as log

SOURCE_NAME = "tplink_host_online"


def get_source(source):
    router_ip = source["router_ip"]
    key = source["key"]
    login_url = "http://{}/".format(router_ip)


    r = requests.post(login_url,json={
        "login": {
            "password": key
        },
        "method": "do"
    })

    token = r.json()["stok"]

    api_url = "http://{}/stok={}/ds".format(router_ip,token)
    # print(api_url)
    r = requests.post(api_url, json={
        "hosts_info":{
            "table":"online_host"
        },
        "method":"get"
    })
    # print(r.json())
    host_list = r.json()["hosts_info"]["online_host"]
    host_name_list = []
    for host in host_list:
        converted_host = host[list(host.keys())[0]]
        parsed_host_name = urllib.parse.unquote(converted_host["hostname"])
        host_name_list.append(parsed_host_name)
    return json.dumps({"host_list":host_name_list})