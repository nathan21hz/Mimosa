import os
import importlib
import utils.log as log

class PushService():
    def __init__(self) -> None:
        self.push_services = None
        self.reload_push_sevice()

    def reload_push_sevice(self):
        push_service_files = os.listdir("./push")
        push_services = {}
        for ps_f in push_service_files:
            push_service_name = ps_f.split(".")[0]
            push_services[push_service_name] = importlib.import_module("push."+push_service_name)
        self.push_services = push_services

    def do_push(self, push_config, data):
        if push_config["type"] in self.push_services:
            try:
                push_res, msg = self.push_services[push_config["type"]].do_push(push_config, data)
                log.info(["Push", push_config["type"]], msg)
            except Exception as e:
                log.error(["Push", push_config["type"]], str(e))
        else:
            log.error(["Push"], "No such push service type: {}.".format(push_config["type"]))
        pass