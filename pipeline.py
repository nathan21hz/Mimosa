import time
import logging

import condition_parser
import data_parser
import push_service
import renderer_parser
import source_loader

logger = logging.getLogger(__name__)

# characters of raw source data kept in a dry run report
DRY_RUN_PREVIEW = 2000


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
        return self.execute(task, hist_data)

    def dry_run(self, task, hist_data):
        """ Run a task up to (not including) push without side effects, return what each step produced """
        trace = {"step": None}
        start = time.time()
        try:
            self.execute(task, hist_data, trace)
        except Exception as e:
            # trace["step"] is left at the step that failed
            trace["error"] = "{}: {}".format(type(e).__name__, e)
        else:
            trace["step"] = None
        trace["duration"] = round(time.time() - start, 2)
        return trace

    def execute(self, task, hist_data, trace=None):
        """ The steps of a run, shared by run() and dry_run().
        With trace (a dict), each step's result is recorded in it and the run stops before push. """
        tracing = trace is not None
        if tracing:
            trace["step"] = "url"
        source = self.resolve_source(task["source"])
        if tracing:
            trace["urls"] = {key: value for key, value in source.items() if key.startswith("*")}
            trace["step"] = "source"
        raw_data = self.sources.load_source(source)
        if tracing:
            raw_text = str(raw_data)
            trace["source"] = {"length": len(raw_text), "preview": raw_text[:DRY_RUN_PREVIEW]}
            trace["step"] = "data"
            trace["data"] = []
        parsed_data = self.data_parsers.parse_data(task["data"], raw_data, trace["data"] if tracing else None)
        if "renderer" in task:
            if tracing:
                trace["step"] = "renderer"
                trace["renderer"] = {}
            output = self.renderers.do_render(task["renderer"], parsed_data, hist_data, trace["renderer"] if tracing else None)
            if tracing:
                trace["renderer"]["output"] = output
            # history is only visible to the renderer
            condition_hist = []
        else:
            output = parsed_data
            condition_hist = hist_data
        if tracing:
            trace["step"] = "condition"
        triggered, details = condition_parser.evaluate(task["condition"], output, condition_hist)
        if tracing:
            trace["condition"] = {"result": bool(triggered), "items": details}
            return parsed_data, bool(triggered)

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
