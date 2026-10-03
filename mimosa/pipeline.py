import re
import json
import time
import logging
from urllib.parse import urljoin

from mimosa import condition_parser, data_parser, push_service, renderer_parser, source_loader
from mimosa.utils.template import render

logger = logging.getLogger(__name__)

# characters of raw source data kept in a dry run report
DRY_RUN_PREVIEW = 2000
# foreach elements detailed in a dry run report (failed ones are added too)
DRY_RUN_FOREACH_ITEMS = 5


def stages_of(task):
    """ The task's stages; a task without "stages" is a single stage of its source and data """
    if "stages" in task:
        return task["stages"]
    return [{"source": task["source"], "data": task["data"]}]


def foreach_items(stage, prev_data):
    """ The list a foreach stage goes through: "$n" of the previous stage's data """
    index = int(stage["foreach"][1:])
    if index >= len(prev_data):
        raise IndexError("foreach {}: no such data in the previous stage (there are {})".format(stage["foreach"], len(prev_data)))
    items = prev_data[index]
    if not isinstance(items, (list, tuple)):
        # str subclasses (e.g. lxml results) are reported as str
        type_name = "str" if isinstance(items, str) else type(items).__name__
        raise TypeError("foreach {}: needs a list, got {} {}".format(stage["foreach"], type_name, match_text(items)[:60]))
    return list(items)


def match_text(item):
    """ Text of a foreach element for match: itself if a string, otherwise its JSON """
    return item if isinstance(item, str) else json.dumps(item, ensure_ascii=False, default=str)


def fill_urls(source, prev_data, prev_url, variables):
    """ Copy of source with url* templates filled with the previous stage's data,
    and relative urls joined to the previous stage's request url """
    filled = dict(source)
    for key, value in source.items():
        if key.startswith("url") and isinstance(value, str):
            url = render(value, prev_data, variables)
            filled[key] = urljoin(prev_url, url) if prev_url else url
    return filled


class Pipeline():
    """ Runs a task once: stages of source -> data, then renderer -> condition -> push """
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
            trace["step"] = "stages"
            trace["stages"] = []
        # each stage sees only the previous stage's data; the last stage's data is the result
        parsed_data, url = None, None
        for stage in stages_of(task):
            stage_trace = {} if tracing else None
            if tracing:
                trace["stages"].append(stage_trace)
            parsed_data, url = self.run_stage(stage, parsed_data, url, stage_trace)
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

    def run_stage(self, stage, prev_data, prev_url, trace=None):
        """ Run one stage, return (its data, its request url; None for foreach).
        prev_data / prev_url are those of the previous stage, None for the first stage. """
        if "foreach" not in stage:
            return self.fetch(stage, prev_data, prev_url, {}, trace)

        tracing = trace is not None
        if tracing:
            trace["step"] = "foreach"
        items = foreach_items(stage, prev_data)
        total = len(items)
        if "match" in stage:
            items = [item for item in items if re.search(stage["match"], match_text(item))]
        matched = len(items)
        if "limit" in stage:
            items = items[:stage["limit"]]
        summary = {"of": stage["foreach"], "total": total, "matched": matched, "visited": len(items), "failed": 0, "items": []}
        if tracing:
            trace["foreach"] = summary
        # one list per data item, an entry per visited element
        columns = [[] for _ in stage["data"]]
        for index, item in enumerate(items):
            if index and stage.get("delay"):
                time.sleep(stage["delay"])
            item_trace = {"item": item} if tracing else None
            try:
                values, _ = self.fetch(stage, prev_data, prev_url, {"item": item}, item_trace)
            except Exception as e:
                summary["failed"] += 1
                if tracing:
                    item_trace["error"] = "{}: {}".format(type(e).__name__, e)
                    if len(summary["items"]) < DRY_RUN_FOREACH_ITEMS * 4:
                        summary["items"].append(item_trace)
                if not stage.get("skip_failed"):
                    raise RuntimeError("foreach element {} ({}) failed: {}: {}".format(
                        index, match_text(item)[:100], type(e).__name__, e)) from e
                logger.warning("Skip failed foreach element {} ({}): {}".format(index, match_text(item)[:100], e))
                continue
            for column, value in zip(columns, values):
                column.append(value)
            if tracing and index < DRY_RUN_FOREACH_ITEMS:
                summary["items"].append(item_trace)
        if tracing:
            trace["data"] = [{"type": item.get("type"), "value": column} for item, column in zip(stage["data"], columns)]
            trace["step"] = None
        return columns, None

    def fetch(self, stage, prev_data, prev_url, variables, trace=None):
        """ Request the stage's source once and parse it, return (data, request url) """
        tracing = trace is not None
        if tracing:
            trace["step"] = "url"
        source = stage["source"]
        if prev_data is not None:
            source = fill_urls(source, prev_data, prev_url, variables)
        source = self.resolve_source(source)
        if tracing:
            trace["urls"] = {key: value for key, value in source.items() if key.startswith("*")}
            trace["step"] = "source"
        raw_data = self.sources.load_source(source)
        if tracing:
            raw_text = str(raw_data)
            trace["source"] = {"length": len(raw_text), "preview": raw_text[:DRY_RUN_PREVIEW]}
            trace["step"] = "data"
            trace["data"] = []
        data = self.data_parsers.parse_data(stage["data"], raw_data, trace["data"] if tracing else None)
        if tracing:
            trace["step"] = None
        url = source.get("*url")
        return data, url if isinstance(url, str) else None

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
        url = render(url_config["base"], parsed_data)
        logger.debug("Get dynamic url: {}.".format(url))
        return url
