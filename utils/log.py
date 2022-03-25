import time
from collections import deque
import config as cfg

def _init():
    global _global_log_record
    _global_log_record = deque([],20)

def get_log_record():
    return "\n".join(_global_log_record)

def add_log_record(log_record_str):
    _global_log_record.append(log_record_str)

def route2str(route):
    template = "[{}]"*len(route)
    return template.format(*route)

def debug(route, info):
    if cfg.get_value("LOG_LEVEL",0) < 2:
        time_str = time.strftime("[%H:%M:%S]", time.localtime())
        log_str = time_str + "[DEBUG]" + route2str(route) + " " + str(info)
        add_log_record(log_str)
        print(log_str)

def info(route, info):
    if cfg.get_value("LOG_LEVEL",0) < 3:
        time_str = time.strftime("[%H:%M:%S]", time.localtime())
        log_str = time_str + "[INFO]" + route2str(route) + " " + str(info)
        add_log_record(log_str)
        print(log_str)

def warning(route, info):
    if cfg.get_value("LOG_LEVEL",0) < 4:
        time_str = time.strftime("[%H:%M:%S]", time.localtime())
        log_str = time_str + "[WARNING]" + route2str(route) + " " + str(info)
        add_log_record(log_str)
        print(log_str)

def error(route, info):
    time_str = time.strftime("[%H:%M:%S]", time.localtime())
    log_str = time_str + "[INFO]" + route2str(route) + " " + str(info)
    add_log_record(log_str)
    print(log_str)
