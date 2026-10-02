import logging

import condition_parser
import data_parser
import push_service
import renderer_parser
import source_loader

logger = logging.getLogger(__name__)


class Pipeline():
    """ Runs a task once: source -> data -> renderer -> condition -> push """
    def __init__(self) -> None:
        self.sources = source_loader.SourceLoader()
        self.data_parsers = data_parser.DataParserLoader()
        self.renderers = renderer_parser.RendererParserLoader()
        self.push_services = push_service.PushService()

    def reload(self):
        """ Reload all modules """
        self.sources.reload_source_loader()
        self.data_parsers.reload_data_parser()
        self.renderers.reload_renderer()
        self.push_services.reload_push_sevice()

    def run(self, task, hist_data):
        """ Run a task once, return (parsed data to be kept as history, whether it pushed).
        Raises before condition and push if the source or any data item fails. """
        source = self.resolve_source(task["source"])
        raw_data = self.sources.load_source(source)
        parsed_data = self.data_parsers.parse_data(task["data"], raw_data)
        if "renderer" in task:
            output = self.renderers.do_render(task["renderer"], parsed_data, hist_data)
            # history is only visible to the renderer
            triggered = condition_parser.condition_parser(task["condition"], output, [])
        else:
            output = parsed_data
            triggered = condition_parser.condition_parser(task["condition"], output, hist_data)

        if triggered:
            self.push(task, output)
        else:
            logger.info("Push condition not satisfied: {}.".format(task["name"]))
        return parsed_data, bool(triggered)

    def push(self, task, output):
        channels = task["push"]
        if isinstance(channels, dict):
            channels = [channels]
        elif not isinstance(channels, list):
            logger.error("Push channel config error: {}.".format(task["name"]))
            return
        for channel in channels:
            self.push_services.do_push(channel, output)

    def resolve_source(self, source):
        """ Return a copy of source with a "*" field resolved for every field starting with "url" """
        resolved = dict(source)
        for key, value in source.items():
            if key.startswith("url"):
                resolved["*" + key] = self.resolve_url(value)
        return resolved

    def resolve_url(self, url_config):
        """ Dynamic URL config -> URL string """
        if isinstance(url_config, str):
            return url_config
        raw_data = self.sources.load_source(self.resolve_source(url_config["source"]))
        parsed_data = self.data_parsers.parse_data(url_config["data"], raw_data)
        url = url_config["base"].format(*parsed_data)
        logger.debug("Get dynamic url: {}.".format(url))
        return url
