import os
import importlib

import config as cfg
import utils.log as log

# init source loader
class SourceLoader():
    def __init__(self) -> None:
        self.sources = None
        self.reload_source_loader()
        
    def reload_source_loader(self):
        sources = {}
        source_files = os.listdir("./source")
        for s_f in source_files:
            source_name = s_f.split(".")[0]
            sources[source_name] = importlib.import_module("source."+source_name)

        external_module_folder = cfg.get_value("EXTERNAL_MODULE_FOLDER", "")
        if external_module_folder != "":
            external_source_files = os.listdir(external_module_folder+"/source")
            for e_s_f in external_source_files:
                e_source_name = e_s_f.split(".")[0]
                sources[e_source_name] = importlib.import_module(external_module_folder.replace("/",".")+".source."+e_source_name)
        self.sources = sources
        
    def load_source(self, source_config):
        if source_config["type"] in self.sources:
            try:
                source_data = self.sources[source_config["type"]].get_source(source_config)
                return source_data
            except Exception as e:
                log.error(["Source", source_config["type"]], str(e))
                return None
        else:
            log.error(["Source"], "No such source type: {}.".format(source_config["type"]))
            return None



