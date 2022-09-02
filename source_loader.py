import os
import importlib

import utils.log as log

# init source loader
class SourceLoader():
    def __init__(self) -> None:
        self.sources = None
        self.reload_source_loader()
        
    def reload_source_loader(self):
        source_files = os.listdir("./source")
        sources = {}
        for s_f in source_files:
            source_name = s_f.split(".")[0]
            sources[source_name] = importlib.import_module("source."+source_name)
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



