import time
import os
def do_push(push_config, data):
    file_name = push_config["file"]
    if not os.path.isfile(file_name):
        return False, "File {} not exist".format(file_name)
    time_label = time.strftime("[%Y-%m-%d %H:%M:%S] ", time.localtime())
    write_string = time_label + push_config["text"].format(*data) + "\n"
    with open(file_name, "a") as f:
        f.write(write_string)
    return True, "OK"