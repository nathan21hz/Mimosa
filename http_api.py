from flask import Flask
import config as cfg
import utils.log
import logging

class HTTPApi():
    def __init__(self, pushworker) -> None:
        self.pw = pushworker
        app = Flask("http_api")
        if cfg.get_value("LOG_LEVEL",0) !=0:
            flask_log = logging.getLogger('werkzeug')
            flask_log.disabled = True
        if cfg.get_value("HTTP_API",False):
            pass
            if cfg.get_value("API_READONLY",True):
                pass
            
    
    

