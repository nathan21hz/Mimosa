import re
import json
import time
import logging

logger = logging.getLogger(__name__)


def matches(text, pattern):
    """ Regex search in a string, or in any string of a list """
    texts = text if isinstance(text, list) else [text]
    return any(re.search(pattern, t) for t in texts)


def lower(value):
    """ Lowercase strings, including those in a list, for ignore_case """
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, list):
        return [lower(v) for v in value]
    return value


# "in" / "contains_*" test substrings for a string and elements for a list
op_dict = {
    "==": lambda a,b: a == b,
    "<": lambda a,b: a < b,
    ">": lambda a,b: a > b,
    "<=": lambda a,b: a <= b,
    ">=": lambda a,b: a >= b,
    "!=": lambda a,b: a != b,
    "in": lambda a,b: a in b,
    "contains_any": lambda a,b: any(x in a for x in b),
    "contains_all": lambda a,b: all(x in a for x in b),
    "matches": matches,
}

def var_parser(var,data,hist_data):
    if type(var) == str:
        if var.startswith("$"):
            var_index = int(var[1:])
            if var_index >= len(data):
                raise IndexError("No such data: {} (there are {})".format(var, len(data)))
            tmp_var = data[var_index]
        elif var.startswith("#"):
            var_index = int(var[1:])
            if var_index >= len(hist_data):
                raise IndexError("No such history data: {} (there are {})".format(var, len(hist_data)))
            tmp_var = hist_data[var_index]
        elif var == "*timestamp":
            tmp_var = int(time.time())
        else:
            tmp_var = var
        return tmp_var
    else:
        return var


def condition_parser(condition_list, data, hist_data):
    return evaluate(condition_list, data, hist_data)[0]


def evaluate(condition_list, data, hist_data):
    """ Evaluate the conditions in order, return (result, details of each condition for the dry run) """
    res = True
    details = []
    for condition in condition_list:
        detail = {key: condition.get(key) for key in ("conn", "var", "op", "target")}
        details.append(detail)
        # get variable
        tmp_var = var_parser(condition["var"],data,hist_data)
        # get target
        tmp_target = var_parser(condition["target"],data,hist_data)
        detail["var_value"], detail["target_value"] = tmp_var, tmp_target
        # compare operation
        if condition["op"] not in op_dict:
            logger.error("Operation error")
            detail["skipped"] = "Unknown op: {}".format(condition["op"])
            continue
        if condition.get("ignore_case"):
            tmp_var = lower(tmp_var)
            if condition["op"] == "matches":
                # lowercasing a pattern could break it (e.g. \D -> \d), use the inline flag instead
                tmp_target = "(?i)" + tmp_target
            else:
                tmp_target = lower(tmp_target)
        try:
            tmp_res = op_dict[condition["op"]](tmp_var,tmp_target)
            if condition.get("not"):
                tmp_res = not tmp_res
        except Exception as e:
            # a failed operation never satisfies the condition, even with "not"
            logger.error("Operation error: {}".format(str(e)))
            detail["error"] = str(e)
            tmp_res = False
        detail["result"] = tmp_res
        # connection operation
        if condition["conn"] not in ["and", "or"]:
            logger.error("Connection op error")
            detail["skipped"] = "Unknown conn: {}".format(condition["conn"])
            continue
        else:
            if condition["conn"] == "and":
                res = res and tmp_res
            elif condition["conn"] == "or":
                res = res or tmp_res
        detail["total"] = res
    return res, details
