import re

def parse_data(raw_data, data_config_item):
    reg_string = data_config_item["exp"]
    all_parsed_data = re.findall(reg_string, str(raw_data))
    return all_parsed_data[data_config_item["index"]]