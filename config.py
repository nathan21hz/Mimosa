import json
import utils.log as log 

def _init():
    global _global_config
    _global_config = {}
 
 
def set_value(key,value):
    _global_config[key] = value
 
 
def get_value(key,defValue=None):
    try:
        return _global_config[key]
    except KeyError:
        return defValue

def load_config(cfg_filename="config.json"):
    with open(cfg_filename,"r") as cfg_file:
        cfg_str = cfg_file.read()
        try:
            config_json = json.loads(cfg_str)
        except Exception as e:
            log.error("Config File Format Error")
            log.error(e)
            exit(1)
    for index in config_json:
        set_value(index,config_json[index])