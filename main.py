import os
import json
import time
import threading
import pickle

import config as cfg
cfg._init()
import utils.log as log

import source_loader
import data_parser
import condition_parser
import push_service

COMMAND = ""

class PushWorker():
    def __init__(self) -> None:
        self.SourceLoader = source_loader.SourceLoader()
        self.DataParser = data_parser.DataParserLoader()
        self.PushService = push_service.PushService()
        self.task_data = {}
        self.dynamic_task = {}
        self.history = {}

        self.reload_task()
        # print(self.last_trigger)
        self.load_history()
        # print(self.history)

    def task_verify(self, task_item):
        """ Verify the task object """
        fields = ["name", "interval","startup_data","source","data","condition","push"]
        for f in fields:
            if f not in task_item:
                return False
        return True

    def reload_task(self):
        """ Relaod tasks """
        task_file = cfg.get_value("TASK_FILE", "tasks.json")
        with open(task_file,"r",encoding='utf-8') as task_file:
            task_data_raw = task_file.read()
        tmp_task_data = json.loads(task_data_raw)
        self.task_data = {}
        self.dynamic_task = {}
        for t_d in tmp_task_data:
            if t_d["type"] == "static":
                if self.task_verify(t_d):
                    self.task_data[t_d["name"]] = t_d
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
                    log.info(["Main"], "Dynamic task loaded: {}".format(d_t))
                else:
                    log.error(["Main"], "Invalid dynamic task:  {}".format(d_t))

    def load_history(self):
        """ Load history from file """
        log.info(["Main"], "Load history.")
        if os.path.isfile("history.pkl"):
            with open("history.pkl","rb") as hist_file:
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
        with open('history.pkl', 'wb') as hist_file:
            pickle.dump(self.history, hist_file)

    def clear_history(self,name=None):
        """ Clear history of a job """
        log.info(["Main"], "Clear history: {}.".format(name))
        if not name:
            tmp_history = {}
            for t_d in self.task_data:
                tmp_history[t_d] = {"time":0,"data":self.task_data[t_d]["startup_data"]}
            self.history = tmp_history
        else:
            if name in self.history:
                self.history[name] = {"time":0,"data":self.task_data[name]["startup_data"]}
            else:
                log.error(["Main"], "No history: {}.".format(name))

    def reload(self):
        """ Reload modules and tasks """
        log.info(["Main"], "Reload started.")
        self.save_history()
        self.SourceLoader.reload_source_loader()
        self.DataParser.reload_data_parser()
        self.PushService.reload_push_sevice()
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
        res = condition_parser.condition_parser(task_data_item["condition"], tmp_parsed_data, self.history[task_data_item["name"]]["data"])
        # print(res)
        self.history[task_data_item["name"]]["data"] = tmp_parsed_data
        if res:
            self.PushService.do_push(task_data_item["push"],tmp_parsed_data)
        else:
            log.info(["Main"], "Push condition not satisfied: {}.".format(task_data_item["name"]))

    def main_loop(self):
        """ Main loop """
        global COMMAND
        log.info(["Main"], "Main worker loop started.")
        while True:
            if COMMAND == "stop":
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
            elif COMMAND == "save":
                self.save_history()
            else:
                # reload dynamic task
                self.load_dynamic_task()
                # update tasks
                threads = []
                for task_data_name in self.task_data:
                    if self.history[task_data_name]["time"] + self.task_data[task_data_name]["interval"] <= time.time():
                        log.info(["Main"], "Updating: {}.".format(task_data_name))
                        tmp_thread = threading.Thread(target=self.update_item, args=[self.task_data[task_data_name],])
                        tmp_thread.start()
                        self.history[task_data_name]["time"] = time.time()
                        threads.append(tmp_thread)
                for t in threads:
                    t.join()
            COMMAND = ""
            time.sleep(0.5)
        # Before stop
        self.save_history()


def control_loop():
    """ Control loop for command input """
    global COMMAND
    pw = PushWorker()
    pw_thread = threading.Thread(target=pw.main_loop)
    pw_thread.start()
    while True:
        try:
            tmp_COMMAND = input()
            if tmp_COMMAND == "stop":
                COMMAND = "stop"
                pw_thread.join()
                break
            elif tmp_COMMAND == "help":
                print("stop: Exit the program; \
                    \nreload: Reload modules and task file; \
                    \nclear [task]: Clear history data of a task; \
                    \nsave: Save the history to file.")
            COMMAND = tmp_COMMAND
            time.sleep(0.05)
        except(KeyboardInterrupt, SystemExit):
            COMMAND = "stop"
            pw_thread.join()
            break

if __name__ == "__main__":
    cfg.load_config()
    control_loop()