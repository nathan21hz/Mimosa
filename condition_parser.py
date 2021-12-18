import json
import time
import utils.log as log

op_dict = {
    "==": lambda a,b: a == b,
    "<": lambda a,b: a < b,
    ">": lambda a,b: a > b,
    "<=": lambda a,b: a <= b,
    ">=": lambda a,b: a >= b,
    "!=": lambda a,b: a != b,
    "in": lambda a,b: a in b
}

def var_parser(var,data,hist_data):
    if type(var) == str:
        if var.startswith("$"):
            var_index = int(var[1:])
            if var_index >= len(data):
                log.error(["Condition"], "Data index error")
            else:
                tmp_var = data[var_index]
        elif var.startswith("#"):
            var_index = int(var[1:])
            if var_index >= len(hist_data):
                log.error(["Condition"], "Data index error")
            else:
                tmp_var = hist_data[var_index]
        elif var == "*timestamp":
            tmp_var = int(time.time())
        else:
            tmp_var = var
        return tmp_var
    else:
        return var


def condition_parser(condition_list, data, hist_data):
    res = True
    for condition in condition_list:
        # get variable
        tmp_var = var_parser(condition["var"],data,hist_data)
        # get target 
        tmp_target = var_parser(condition["target"],data,hist_data)
        # print(tmp_var,tmp_target)
        # compare operation
        if condition["op"] not in ["==", "<", ">", "<=", ">=", "!=", "in"]:
            log.error(["Condition"], "Operation error")
            continue
        try:
            tmp_res = op_dict[condition["op"]](tmp_var,tmp_target)
        except Exception as e:
            log.error(["Condition"], "Operation error: {}".format(str(e)))
            tmp_res = False
        # connection operation
        if condition["conn"] not in ["and", "or"]:
            log.error(["Condition"], "Connection op error")
            continue
        else:
            if condition["conn"] == "and":
                res = res and tmp_res
            elif condition["conn"] == "or":
                res = res or tmp_res
    return res
