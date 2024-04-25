import os
import importlib

import config as cfg
import utils.log as log

class RendererParserLoader():
    def __init__(self) -> None:
        self.renderer = None
        self.reload_renderer()

    def reload_renderer(self):
        renderer = {}
        renderer_files = os.listdir("./renderer")
        for r_f in renderer_files:
            renderer_name = r_f.split(".")[0]
            if renderer_name in renderer:
                importlib.reload(renderer[renderer_name])
            else:
                renderer[renderer_name] = importlib.import_module("renderer."+renderer_name)

        external_module_folder = cfg.get_value("EXTERNAL_MODULE_FOLDER", "")
        if external_module_folder != "":
            external_renderer_files = os.listdir(external_module_folder+"/renderer")
            for e_r_f in external_renderer_files:
                e_renderer_name = e_r_f.split(".")[0]
                if e_renderer_name in renderer:
                    importlib.reload(renderer[e_renderer_name])
                else:
                    renderer[e_renderer_name] = importlib.import_module(external_module_folder.replace("/",".")+".renderer."+e_renderer_name)
    
        self.renderer = renderer

    def do_render(self, renderer_config, data, hist_data):
        if renderer_config["type"] in self.renderer:
            try:
                rendered_data = self.renderer[renderer_config["type"]].do_render(renderer_config, data, hist_data)
                log.info(["Renderer", renderer_config["type"]], rendered_data)
                return(rendered_data)
            except Exception as e:
                log.error(["Renderer", renderer_config["type"]], str(e))
        else:
            log.error(["Renderer"], "No such renderer type: {}.".format(renderer_config["type"]))
        return [0]