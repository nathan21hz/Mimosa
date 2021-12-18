import time
import config as cfg

def route2str(route):
    template = "[{}]"*len(route)
    return template.format(*route)

def debug(route, info):
    if cfg.get_value("LOG_LEVEL",0) < 2:
        time_str = time.strftime("[%H:%M:%S]", time.localtime())
        print(time_str + "[DEBUG]" + route2str(route) + " " + str(info))

def info(route, info):
    if cfg.get_value("LOG_LEVEL",0) < 3:
        time_str = time.strftime("[%H:%M:%S]", time.localtime())
        print(time_str + "[INFO]" + route2str(route) + " " + str(info))

def warning(route, info):
    if cfg.get_value("LOG_LEVEL",0) < 4:
        time_str = time.strftime("[%H:%M:%S]", time.localtime())
        print(time_str + "[WARNING]" + route2str(route) + " " + str(info))

def error(route, info):
    time_str = time.strftime("[%H:%M:%S]", time.localtime())
    print(time_str + "[INFO]" + route2str(route) + " " + str(info))
