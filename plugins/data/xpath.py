from lxml import etree
from lxml import html


def to_text(result):
    """ Plain value of an xpath result: str for text / attributes, text content for elements """
    if isinstance(result, str):
        return str(result)
    if isinstance(result, etree._Element):
        return result.text_content()
    return result


def parse_data(raw_data, data_config_item):
    tree = html.fromstring(raw_data)
    # "*": all results as a list
    if data_config_item["index"] == "*":
        results = tree.xpath(data_config_item["xpath"])
        # expressions like count() give a single value
        if not isinstance(results, list):
            results = [results]
        return [to_text(r) for r in results]
    if data_config_item["index"] >= 0:
        res = tree.xpath(data_config_item["xpath"])[data_config_item["index"]]
    else:
        res = tree.xpath(data_config_item["xpath"])
        res = "".join(res)
    return res
