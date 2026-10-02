import os
import importlib
import logging

import config as cfg

logger = logging.getLogger(__name__)

# init source loader
class SourceLoader():
    def __init__(self) -> None:
        self.sources = {}
        self.reload_source_loader()
        
    def reload_source_loader(self):
        source_files = os.listdir("./source")
        for s_f in source_files:
            source_name = s_f.split(".")[0]
            if source_name in self.sources:
                logger.info("Reload module " + source_name)
                importlib.reload(self.sources[source_name])
            else:
                logger.info("Load module " + source_name)
                self.sources[source_name] = importlib.import_module("source."+source_name)

        external_module_folder = cfg.get_value("EXTERNAL_MODULE_FOLDER", "")
        if external_module_folder != "":
            external_source_files = os.listdir(external_module_folder+"/source")
            for e_s_f in external_source_files:
                e_source_name = e_s_f.split(".")[0]
                if e_source_name in self.sources:
                    logger.info("Reload external module " + e_source_name)
                    importlib.reload(self.sources[e_source_name])
                else:
                    logger.info("Load external module " + e_source_name)
                    self.sources[e_source_name] = importlib.import_module(external_module_folder.replace("/",".")+".source."+e_source_name)
        
    def load_source(self, source_config):
        """ Load raw data from the source, raise if it fails """
        if source_config["type"] not in self.sources:
            raise ValueError("No such source type: {}.".format(source_config["type"]))
        try:
            source_data = self.sources[source_config["type"]].get_source(source_config)
        except Exception as e:
            raise RuntimeError("Source {} failed: {!r}".format(source_config["type"], e)) from e
        if source_data is None:
            raise RuntimeError("Source {} returned nothing.".format(source_config["type"]))
        return source_data



