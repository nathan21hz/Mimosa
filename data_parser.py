import os
import importlib
import copy
import logging

import config as cfg

logger = logging.getLogger(__name__)


# Data parser loader
class DataParserLoader():
    def __init__(self) -> None:
        self.data_parsers = {}
        self.reload_data_parser()
        
    def reload_data_parser(self):
        data_parser_files = os.listdir("./data")
        for dp_f in data_parser_files:
            data_parser_name = dp_f.split(".")[0]
            if data_parser_name in self.data_parsers:
                logger.info("Reload module " + data_parser_name)
                importlib.reload(self.data_parsers[data_parser_name])
            else:
                logger.info("Load module " + data_parser_name)
                self.data_parsers[data_parser_name] = importlib.import_module("data."+data_parser_name)

        external_module_folder = cfg.get_value("EXTERNAL_MODULE_FOLDER", "")
        if external_module_folder != "":
            external_data_parser_files = os.listdir(external_module_folder+"/data")
            for e_dp_f in external_data_parser_files:
                e_data_parser_name = e_dp_f.split(".")[0]
                if e_data_parser_name in self.data_parsers:
                    logger.info("Reload external module " + e_data_parser_name)
                    importlib.reload(self.data_parsers[e_data_parser_name])
                else:
                    logger.info("Load external module " + e_data_parser_name)
                    self.data_parsers[e_data_parser_name] = importlib.import_module(external_module_folder.replace("/",".")+".data."+e_data_parser_name)

    def parse_data(self, data_config, raw_data):
        """ Parse raw data with each data config item, raise if any item fails """
        parsed_data = []
        for index, data_config_item in enumerate(data_config):
            if data_config_item["type"] not in self.data_parsers:
                raise ValueError("No such data type: {}.".format(data_config_item["type"]))
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
                raise RuntimeError("Data item {} ({}) failed: {!r}".format(index, data_config_item["type"], e)) from e
        logger.debug(str(parsed_data))
        return parsed_data