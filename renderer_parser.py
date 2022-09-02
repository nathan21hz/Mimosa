import os
import importlib

import config as cfg
import utils.log as log

class RendererParserLoader():
    def __init__(self) -> None:
        self.rederer = None
        self.reload_renderer()

    def reload_renderer(self):
        rederer = {}
        rederer_files = os.listdir("./renderer")
        for r_f in rederer_files:
            rederer_name = r_f.split(".")[0]
            rederer[rederer_name] = importlib.import_module("renderer."+rederer_name)

        external_module_folder = cfg.get_value("EXTERNAL_MODULE_FOLDER", "")
        if external_module_folder != "":
            external_rederer_files = os.listdir(external_module_folder+"/renderer")
            for e_r_f in external_rederer_files:
                e_rederer_name = e_r_f.split(".")[0]
                rederer[e_rederer_name] = importlib.import_module(external_module_folder.replace("/",".")+".renderer."+e_rederer_name)
    
        self.rederer = rederer

    def do_render(self, renderer_config, data, hist_data):
        if renderer_config["type"] in self.rederer:
            try:
                rendered_data = self.rederer[renderer_config["type"]].do_render(renderer_config, data, hist_data)
                log.info(["Renderer", renderer_config["type"]], rendered_data)
                return(rendered_data)
            except Exception as e:
                log.error(["Renderer", renderer_config["type"]], str(e))
        else:
            log.error(["Renderer"], "No such renderer type: {}.".format(renderer_config["type"]))
        return [0]