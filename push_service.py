import os
import importlib

import config as cfg
import utils.log as log

class PushService():
    def __init__(self) -> None:
        self.push_services = None
        self.reload_push_sevice()

    def reload_push_sevice(self):
        push_services = {}
        push_service_files = os.listdir("./push")
        for ps_f in push_service_files:
            push_service_name = ps_f.split(".")[0]
            if push_service_name in push_services:
                importlib.reload(push_services[push_service_name])
            else:
                push_services[push_service_name] = importlib.import_module("push."+push_service_name)

        external_module_folder = cfg.get_value("EXTERNAL_MODULE_FOLDER", "")
        if external_module_folder != "":
            external_push_service_files = os.listdir(external_module_folder+"/push")
            for e_ps_f in external_push_service_files:
                e_push_service_name = e_ps_f.split(".")[0]
                if e_push_service_name in push_services:
                    importlib.reload(push_services[e_push_service_name])
                else:
                    push_services[e_push_service_name] = importlib.import_module(external_module_folder.replace("/",".")+".push."+e_push_service_name)

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