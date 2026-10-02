import logging

logger = logging.getLogger(__name__)

def do_render(render_config, data, hist_data):
    logger.debug("Current: %s, history: %s", data, hist_data)
    target_list = render_config["target_list"]
    for item in data[0]:
        for target in target_list:
            if target in item["maker"] or target in item["actor"]:
                pid  = item["pID"]
                pname = item["pName"]
                return [1, pid, pname]

    return [0, "", ""]