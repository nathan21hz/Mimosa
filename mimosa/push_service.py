import os
import importlib
import logging

from mimosa import config as cfg
from mimosa.utils.plugins import builtin_folder, module_names

logger = logging.getLogger(__name__)

class PushService():
    def __init__(self) -> None:
        self.push_services = {}
        self.reload_push_sevice()

    def reload_push_sevice(self):
        push_service_files = module_names(builtin_folder("push"))
        for ps_f in push_service_files:
            push_service_name = ps_f.split(".")[0]
            if push_service_name in self.push_services:
                logger.info("Reload module " + push_service_name)
                importlib.reload(self.push_services[push_service_name])
            else:
                logger.info("Load module " + push_service_name)
                self.push_services[push_service_name] = importlib.import_module("plugins.push."+push_service_name)

        external_module_folder = cfg.get_value("EXTERNAL_MODULE_FOLDER", "")
        if external_module_folder != "":
            external_push_service_files = module_names(external_module_folder+"/push")
            for e_ps_f in external_push_service_files:
                e_push_service_name = e_ps_f.split(".")[0]
                if e_push_service_name in self.push_services:
                    logger.info("Reload external module " + e_push_service_name)
                    importlib.reload(self.push_services[e_push_service_name])
                else:
                    logger.info("Load external module " + e_push_service_name)
                    self.push_services[e_push_service_name] = importlib.import_module(external_module_folder.replace("/",".")+".push."+e_push_service_name)

    def do_push(self, push_config, data):
        if push_config["type"] in self.push_services:
            try:
                push_res, msg = self.push_services[push_config["type"]].do_push(push_config, data)
                logger.info("%s: %s", push_config["type"], msg)
            except Exception as e:
                logger.error("%s: %s", push_config["type"], e)
        else:
            logger.error("No such push service type: {}.".format(push_config["type"]))
        pass