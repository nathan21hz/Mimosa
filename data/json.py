import json

# errors meaning an element has no such key / index
MISSING_ERRORS = (KeyError, IndexError, TypeError)


def parse_data(raw_data, data_config_item):
    # raw text from the source, or already parsed data in postprocess
    data = json.loads(raw_data) if isinstance(raw_data, (str, bytes)) else raw_data
    return walk(data, data_config_item["route"], data_config_item.get("skip_missing", False))


def walk(data, route, skip_missing):
    """ Follow the route; "*" applies the rest of the route to every item of a list (or value of an object) """
    for i, step in enumerate(route):
        if step == "*":
            if isinstance(data, dict):
                items = data.values()
            elif isinstance(data, list):
                items = data
            else:
                raise TypeError("'*' needs a list or object, got {}".format(type(data).__name__))
            results = []
            for item in items:
                try:
                    results.append(walk(item, route[i + 1:], skip_missing))
                except MISSING_ERRORS:
                    if not skip_missing:
                        raise
            return results
        data = data[step]
    return data
