import os
import importlib
import copy

import config as cfg
import utils.log as log


# Data parser loader
class DataParserLoader():
    def __init__(self) -> None:
        self.data_parsers = None
        self.reload_data_parser()
        
    def reload_data_parser(self):
        data_parsers = {}
        data_parser_files = os.listdir("./data")
        for dp_f in data_parser_files:
            data_parser_name = dp_f.split(".")[0]
            if data_parser_name in data_parsers:
                importlib.reload(data_parsers[data_parser_name])
            else:
                data_parsers[data_parser_name] = importlib.import_module("data."+data_parser_name)

        external_module_folder = cfg.get_value("EXTERNAL_MODULE_FOLDER", "")
        if external_module_folder != "":
            external_data_parser_files = os.listdir(external_module_folder+"/data")
            for e_dp_f in external_data_parser_files:
                e_data_parser_name = e_dp_f.split(".")[0]
                if e_data_parser_name in data_parsers:
                    importlib.reload(data_parsers[e_data_parser_name])
                else:
                    data_parsers[e_data_parser_name] = importlib.import_module(external_module_folder.replace("/",".")+".data."+e_data_parser_name)
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
                    log.error(["Data", data_config_item["type"]], str(e))
                    parsed_data.append(None)
            else:
                log.error(["Data"], "No such data type: {}.".format(data_config_item["type"]))
                parsed_data.append(None)
        log.debug(["Data"], str(parsed_data))
        return parsed_data