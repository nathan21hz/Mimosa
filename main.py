import os
import json
import time
import threading
import pickle

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
        self.config_data = {}
        self.history = {}

        self.reload_config()
        # print(self.last_trigger)
        self.load_history()
        # print(self.history)

    def reload_config(self):
        with open("config.json","r",encoding='utf-8') as config_file:
            config_data_raw = config_file.read()
        tmp_config_data = json.loads(config_data_raw)
        self.config_data = {}
        for c_d in tmp_config_data:
            self.config_data[c_d["name"]] = c_d

    def load_history(self):
        print("[Main] Load history.")
        if os.path.isfile("history.pkl"):
            with open("history.pkl","rb") as hist_file:
                tmp_history = pickle.load(hist_file)
        else:
            tmp_history = {}
        del_list = []
        for h in tmp_history:
            if h not in self.config_data:
                del_list.append(h)
        for h in del_list:
            del tmp_history[h]
        for c_d in self.config_data:
            if c_d not in tmp_history:
                tmp_history[c_d] = {"time":0,"data":self.config_data[c_d]["startup_data"]}
        self.history = tmp_history

    def save_history(self):
        print("[Main] Save history.")
        with open('history.pkl', 'wb') as hist_file:
            pickle.dump(self.history, hist_file)

    def clear_history(self,name=None):
        print("[Main] Clear history: {}.".format(name))
        if not name:
            tmp_history = {}
            for c_d in self.config_data:
                tmp_history[c_d] = {"time":0,"data":self.config_data[c_d]["startup_data"]}
            self.history = tmp_history
        else:
            self.history[name] = {"time":0,"data":self.config_data[name]["startup_data"]}

    def reload(self):
        print("[Main] Reloading.")
        self.save_history()
        self.SourceLoader.reload_source_loader()
        self.DataParser.reload_data_parser()
        self.PushService.reload_push_sevice()
        self.reload_config()
        self.load_history()

    def update_item(self, config_data_item):
        if type(config_data_item["source"]["url"]) == str:
            tmp_raw_data = self.SourceLoader.load_source(config_data_item["source"])
        else:
            tmp_url_raw_data = self.SourceLoader.load_source(config_data_item["source"]["url"]["source"])
            tmp_url_parsed_data = self.DataParser.parse_data(config_data_item["source"]["url"]["data"], tmp_url_raw_data)
            config_data_item["source"]["*url"] = config_data_item["source"]["url"]["base"].format(*tmp_url_parsed_data)
            # print(config_data_item)
            tmp_raw_data = self.SourceLoader.load_source(config_data_item["source"])
            
        #print(tmp_raw_data)
        tmp_parsed_data = self.DataParser.parse_data(config_data_item["data"], tmp_raw_data)
        #print(tmp_parsed_data)
        res = condition_parser.condition_parser(config_data_item["condition"], tmp_parsed_data, self.history[config_data_item["name"]]["data"])
        # print(res)
        self.history[config_data_item["name"]]["data"] = tmp_parsed_data
        if res:
            self.PushService.do_push(config_data_item["push"],tmp_parsed_data)
        else:
            print("[Main][{}] No update.".format(config_data_item["name"]))

    def main_loop(self):
        global COMMAND
        print("[Main] Main worker loop started.")
        while True:
            if COMMAND == "stop":
                print("[Main] Stopping.")
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
                threads = []
                for config_data_name in self.config_data:
                    if self.history[config_data_name]["time"] + self.config_data[config_data_name]["interval"] <= time.time():
                        print("[Main] {} is updating".format(config_data_name))
                        tmp_thread = threading.Thread(target=self.update_item, args=[self.config_data[config_data_name],])
                        tmp_thread.start()
                        self.history[config_data_name]["time"] = time.time()
                        threads.append(tmp_thread)
                for t in threads:
                    t.join()
            COMMAND = ""
            time.sleep(0.5)
        
        self.save_history()


def control_loop():
    global COMMAND
    pw = PushWorker()
    pw_thread = threading.Thread(target=pw.main_loop)
    pw_thread.start()
    while True:
        tmp_COMMAND = input()
        if tmp_COMMAND == "stop":
            COMMAND = "stop"
            pw_thread.join()
            break
        COMMAND = tmp_COMMAND
        time.sleep(0.05)

if __name__ == "__main__":
    control_loop()