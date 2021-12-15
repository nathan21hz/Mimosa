import os
import importlib
import copy


# Data parser loader
class DataParserLoader():
    def __init__(self) -> None:
        self.data_parsers = None
        self.reload_data_parser()
        
    def reload_data_parser(self):
        data_parser_files = os.listdir("./data")
        data_parsers = {}
        for dp_f in data_parser_files:
            data_parser_name = dp_f.split(".")[0]
            data_parsers[data_parser_name] = importlib.import_module("data."+data_parser_name)
        self.data_parsers = data_parsers

    def parse_data(self, data_config, raw_data):
        parsed_data = []
        for data_config_item in data_config:
            if data_config_item["type"] in self.data_parsers:
                try:
                    tmp_raw_data = copy.deepcopy(raw_data)
                    tmp_parsed_data = self.data_parsers[data_config_item["type"]].parse_data(tmp_raw_data, data_config_item)
                    while "postprocess" in data_config_item:
                        data_config_item = data_config_item["postprocess"]
                        tmp_raw_data = copy.deepcopy(tmp_parsed_data)
                        tmp_parsed_data = self.data_parsers[data_config_item["type"]].parse_data(tmp_raw_data, data_config_item)
                    parsed_data.append(tmp_parsed_data)
                    del tmp_raw_data
                except Exception as e:
                    print("[Data][{}] {}".format(data_config_item["type"], str(e)))
                    parsed_data.append(None)
            else:
                print("[Data] No such data type: {}.".format(data_config_item["type"]))
                parsed_data.append(None)
        return parsed_data