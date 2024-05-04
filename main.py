import os
import json
from sys import api_version
import time
import threading
import pickle
import requests

import config as cfg
cfg._init()
import utils.log as log
log._init()

import source_loader
import data_parser
import renderer_parser
import condition_parser
import push_service
import http_api

COMMAND = ""

class PushWorker():
    def __init__(self) -> None:
        self.SourceLoader = source_loader.SourceLoader()
        self.DataParser = data_parser.DataParserLoader()
        self.RendererParser = renderer_parser.RendererParserLoader()
        self.PushService = push_service.PushService()
        self.task_data = {}
        self.dynamic_task = {}
        self.online_task = {}
        self.history = {}

        self.reload_task()
        # print(self.last_trigger)
        self.load_history()
        # print(self.history)

    def task_verify(self, task_item):
        """ Verify the task object """
        fields = ["name", "interval","startup_data","source","data","condition","push"]
        try:
            for f in fields:
                if f not in task_item:
                    return False
        except:
            return False
        return True

    def reload_task(self):
        """ Relaod tasks """
        task_file = cfg.get_value("TASK_FILE", "tasks.json")
        if os.path.exists(task_file):
            with open(task_file,"r",encoding='utf-8') as task_file:
                task_data_raw = task_file.read()
            try:
                tmp_task_data = json.loads(task_data_raw)
            except:
                log.error(["Main"], "Invalid task config file.")
                return
        else:
            log.error(["Main"], "No task config file.")
            return
        self.task_data = {}
        self.online_task = {}
        self.dynamic_task = {}
        for t_d in tmp_task_data:
            if t_d["type"] == "static":
                if self.task_verify(t_d):
                    self.task_data[t_d["name"]] = t_d
                    self.task_data[t_d["name"]]["running"] = self.task_data[t_d["name"]].get("running", True)

                    log.info(["Main"], "Static task loaded: {}".format(t_d["name"]))
                else:
                    log.error(["Main"], "Invalid static task:  {}".format(t_d.get("name")))
            elif t_d["type"] == "dynamic":
                self.dynamic_task[t_d["name"]] = t_d
                self.dynamic_task[t_d["name"]]["last_update"] = 0.0
        self.load_dynamic_task()

    def load_dynamic_task(self):
        """ Load the dynamic tasks """
        for d_t in self.dynamic_task:
            if self.dynamic_task[d_t]["last_update"] + self.dynamic_task[d_t]["update_interval"] <= time.time():
                self.dynamic_task[d_t]["last_update"] = time.time()
                self.dynamic_task[d_t]["task_source"] = self.preprocess_source(self.dynamic_task[d_t]["task_source"])
                tmp_raw_task = self.SourceLoader.load_source(self.dynamic_task[d_t]["task_source"])
                tmp_task = json.loads(tmp_raw_task)
                if self.task_verify(tmp_task):
                    self.task_data[d_t] = tmp_task
                    self.task_data[d_t]["running"] = True
                    log.info(["Main"], "Dynamic task loaded: {}".format(d_t))
                else:
                    log.error(["Main"], "Invalid dynamic task:  {}".format(d_t))

    def load_online_task(self, tmp_online_task):
        """ Load online task """
        if self.task_verify(tmp_online_task):
            tmp_online_task["name"] = "online_" + tmp_online_task["name"]
            tmp_online_task["type"] = "online"
            tmp_online_task["running"] = True
            self.online_task[tmp_online_task["name"]] = tmp_online_task

            self.history[tmp_online_task["name"]] = {"time":0,"data":tmp_online_task["startup_data"]}

            return True
        else:
            return False

    def del_online_task(self, name):
        """ Delete online task """
        if not name or name not in self.online_task:
            return False
        else:
            del self.online_task[name]
            return True

    def load_history(self):
        """ Load history from file """
        log.info(["Main"], "Load history.")
        hist_file_name = cfg.get_value("HISTORY_FILE", "history.pkl")
        if os.path.isfile(hist_file_name):
            with open(hist_file_name,"rb") as hist_file:
                tmp_history = pickle.load(hist_file)
        else:
            tmp_history = {}
        del_list = []
        for h in tmp_history:
            if h not in self.task_data:
                del_list.append(h)
        for h in del_list:
            del tmp_history[h]
        for t_d in self.task_data:
            if t_d not in tmp_history:
                tmp_history[t_d] = {"time":0,"data":self.task_data[t_d]["startup_data"]}
        self.history = tmp_history

    def save_history(self):
        """ Save history to file """
        log.info(["Main"], "Save history to file.")
        hist_file_name = cfg.get_value("HISTORY_FILE", "history.pkl")
        with open(hist_file_name, 'wb') as hist_file:
            pickle.dump(self.history, hist_file)

    def clear_history(self,name=None):
        """ Clear history of a job """
        log.info(["Main"], "Clear history: {}.".format(name))
        if not name:
            log.error(["Main"], "Please specify the task name.")
        else:
            if name in self.task_data:
                self.history[name] = {"time":0,"data":self.task_data[name]["startup_data"]}
            elif name in self.online_task:
                self.history[name] = {"time":0,"data":self.online_task[name]["startup_data"]}
            else:
                log.error(["Main"], "No such task: {}.".format(name))

    def start_task(self, name):
        if not name:
            log.error(["Main"], "Please specify the task name.")
        else:
            if name in self.task_data:
                self.task_data[name]["running"] = True
                log.info(["Main"], "Task is started: {}.".format(name))

            elif name in self.online_task:
                self.online_task[name]["running"] = True
                log.info(["Main"], "Task is started: {}.".format(name))
            else:
                log.error(["Main"], "No such task: {}.".format(name))

    def stop_task(self, name):
        if not name:
            log.error(["Main"], "Please specify the task name.")
        else:
            if name in self.task_data:
                self.task_data[name]["running"] = False
                log.info(["Main"], "Task is stopped: {}.".format(name))

            elif name in self.online_task:
                self.online_task[name]["running"] = False
                log.info(["Main"], "Task is stopped: {}.".format(name))
            else:
                log.error(["Main"], "No such task: {}.".format(name))


    def reload(self):
        """ Reload modules and tasks """
        log.info(["Main"], "Reload started.")
        self.save_history()
        log.info(["Main"], "Reloading modules.")
        self.SourceLoader.reload_source_loader()
        self.DataParser.reload_data_parser()
        self.PushService.reload_push_sevice()
        log.info(["Main"], "Reloading tasks.")
        self.reload_task()
        self.load_history()
        log.info(["Main"], "Reload finished.")
    
    def dynamic_url_load(self,url_config):
        """ Dynamic URL object -> URL string """
        if type(url_config) == str:
            return url_config
        else:
            tmp_url = self.dynamic_url_load(url_config["source"]["url"])
            url_config["source"]["*url"] = tmp_url
            tmp_url_raw_data = self.SourceLoader.load_source(url_config["source"])
            tmp_url_parsed_data = self.DataParser.parse_data(url_config["data"], tmp_url_raw_data)
            # print(url_config["base"].format(*tmp_url_parsed_data))
            gen_url = url_config["base"].format(*tmp_url_parsed_data)
            log.debug(["Main"], "Get dynamic url: {}.".format(gen_url))
            return gen_url

    def preprocess_source(self,task_source):
        """ Generate *url fields for all fields starts with url for task source """
        tmp_dynamic_urls = {}
        for item in task_source:
            if item.startswith("url"):
                tmp_dynamic_urls["*"+item] = self.dynamic_url_load(task_source[item])
        for dynamic_url in tmp_dynamic_urls:
            task_source[dynamic_url] = tmp_dynamic_urls[dynamic_url]
        # print(task_source)
        return task_source

    def update_item(self, task_data_item):
        """ Update a job """
        # load url
        task_data_item["source"] = self.preprocess_source(task_data_item["source"])
        # print(task_data_item)
        tmp_raw_data = self.SourceLoader.load_source(task_data_item["source"])
        #print(tmp_raw_data)
        tmp_parsed_data = self.DataParser.parse_data(task_data_item["data"], tmp_raw_data)
        #print(tmp_parsed_data)
        if "renderer" in task_data_item:
            tmp_rendered_data = self.RendererParser.do_render(task_data_item["renderer"], tmp_parsed_data, self.history[task_data_item["name"]]["data"])
            res = condition_parser.condition_parser(task_data_item["condition"], tmp_rendered_data, [])
        else:
            tmp_rendered_data = tmp_parsed_data
            res = condition_parser.condition_parser(task_data_item["condition"], tmp_rendered_data, self.history[task_data_item["name"]]["data"])
        # print(res)

        self.history[task_data_item["name"]]["data"] = tmp_parsed_data

        if res:
            if isinstance(task_data_item["push"],dict):
                self.PushService.do_push(task_data_item["push"],tmp_rendered_data)
            elif isinstance(task_data_item["push"],list):
                for push_channel in task_data_item["push"]:
                    self.PushService.do_push(push_channel,tmp_rendered_data)
            else:
                log.error(["Main"], "Push channel config error: {}.".format(task_data_item["name"]))
        else:
            log.info(["Main"], "Push condition not satisfied: {}.".format(task_data_item["name"]))

    def main_loop(self):
        """ Main loop """
        global COMMAND
        log.info(["Main"], "Main worker loop started.")
        loop_count = 0
        while True:
            loop_count += 1
            if COMMAND == "exit":
                log.info(["Main"], "Stopping.")
                break
            elif COMMAND == "reload":
                self.reload()
            elif COMMAND.startswith("clear"):
                comm_argv = COMMAND.split(" ")
                if len(comm_argv) == 1:
                    self.clear_history()
                else:
                    self.clear_history(comm_argv[1])
            elif COMMAND.startswith("start"):
                comm_argv = COMMAND.split(" ")
                if len(comm_argv) == 1:
                    log.info(["Main"], "Please specify the task.")
                else:
                    self.start_task(comm_argv[1])
            elif COMMAND.startswith("stop"):
                comm_argv = COMMAND.split(" ")
                if len(comm_argv) == 1:
                    log.info(["Main"], "Please specify the task.")
                else:
                    self.stop_task(comm_argv[1])
            elif COMMAND == "save":
                self.save_history()
            else:
                # reload dynamic task
                self.load_dynamic_task()
                # update tasks
                threads = []
                # update local tasks
                for task_data_name in self.task_data:
                    if self.history[task_data_name]["time"] + self.task_data[task_data_name]["interval"] <= time.time() \
                    and self.task_data[task_data_name]["running"]:
                        log.info(["Main"], "Updating: {}.".format(task_data_name))
                        tmp_thread = threading.Thread(target=self.update_item, args=[self.task_data[task_data_name],])
                        tmp_thread.start()
                        self.history[task_data_name]["time"] = time.time()
                        threads.append(tmp_thread)
                # update online tasks
                for online_task_name in self.online_task:
                    if self.history[online_task_name]["time"] + self.online_task[online_task_name]["interval"] <= time.time() \
                    and self.online_task[online_task_name]["running"]:
                        log.info(["Main"], "Updating: {}.".format(online_task_name))
                        tmp_thread = threading.Thread(target=self.update_item, args=[self.online_task[online_task_name],])
                        tmp_thread.start()
                        self.history[online_task_name]["time"] = time.time()
                        threads.append(tmp_thread)
                for t in threads:
                    t.join()
            COMMAND = ""
            time.sleep(0.5)
            if loop_count == 1000:
                self.save_history()
                loop_count = 0
        # Before stop
        self.save_history()


def control_loop():
    """ Control loop for command input """
    global COMMAND
    pw = PushWorker()
    pw_thread = threading.Thread(target=pw.main_loop)
    pw_thread.start()
    if cfg.get_value("HTTP_API", False):
        api = http_api.HTTPApi(pw)
        api_thread = threading.Thread(target=api.run)
        api_thread.daemon = True
        api_thread.start()
    while True:
        try:
            tmp_COMMAND = input()
            if tmp_COMMAND == "exit":
                COMMAND = "exit"
                pw_thread.join()
                exit(0)
            elif tmp_COMMAND == "help":
                print("exit: Exit the program; \
                    \nreload: Reload modules and task file; \
                    \nstart <task>: Start the task;\
                    \nstop <task>: Stop the task;\
                    \nclear [task]: Clear history data of a task; \
                    \nsave: Save the history to file.")
            else:
                COMMAND = tmp_COMMAND
            time.sleep(0.05)
        except(KeyboardInterrupt, SystemExit):
            COMMAND = "exit"
            pw_thread.join()
            exit(0)
                    

LOGO = """
    __  ___ _                               
   /  |/  /(_)____ ___   ____   _____ ____ _
  / /|_/ // // __ `__ \ / __ \ / ___// __ `/
 / /  / // // / / / / // /_/ /(__  )/ /_/ / 
/_/  /_//_//_/ /_/ /_/ \____//____/ \__,_/ 
  An AIO Clawer/Monitor/MsgPush Framework
"""

if __name__ == "__main__":
    print(LOGO)
    cfg.load_config()
    control_loop()