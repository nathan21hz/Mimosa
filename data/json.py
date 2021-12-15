import  json

def parse_data(raw_data, data_config_item):
    json_data = json.loads(raw_data)
    for step in data_config_item["route"]:
        json_data = json_data[step]
    return json_data