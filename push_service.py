import os
import importlib


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
                print("[Push][{}]  {}.".format(push_config["type"], msg))
            except Exception as e:
                print("[Push][{}]  {}.".format(push_config["type"], str(e)))
        else:
            print("[Push] No such push service type: {}.".format(push_config["type"]))
        pass