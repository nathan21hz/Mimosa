from lxml import etree
from lxml import html

def parse_data(raw_data, data_config_item):
    tree = html.fromstring(raw_data)
    if data_config_item["index"] >= 0:
        res = tree.xpath(data_config_item["xpath"])[data_config_item["index"]]
    else:
        res = tree.xpath(data_config_item["xpath"])
        res = "".join(res)
    return res