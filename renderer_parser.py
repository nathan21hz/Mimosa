import os
import importlib
import utils.log as log

class RendererParserLoader():
    def __init__(self) -> None:
        self.rederer_parsers = None
        self.reload_renderer_parser()

    def reload_renderer_parser(self):
        rederer_parser_files = os.listdir("./renderer")
        rederer_parsers = {}
        for rp_f in rederer_parser_files:
            rederer_parser_name = rp_f.split(".")[0]
            rederer_parsers[rederer_parser_name] = importlib.import_module("renderer."+rederer_parser_name)
        self.rederer_parsers = rederer_parsers

    def do_render(self, renderer_config, data, hist_data):
        if renderer_config["type"] in self.rederer_parsers:
            try:
                rendered_data = self.rederer_parsers[renderer_config["type"]].do_render(renderer_config, data, hist_data)
                log.info(["Renderer", renderer_config["type"]], rendered_data)
                return(rendered_data)
            except Exception as e:
                log.error(["Renderer", renderer_config["type"]], str(e))
        else:
            log.error(["Renderer"], "No such renderer type: {}.".format(renderer_config["type"]))
        return [0]