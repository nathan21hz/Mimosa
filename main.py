import os
import time
import queue
import signal
import logging
import threading
from concurrent.futures import Future

import config as cfg
import utils.log as log
from worker import Worker
from dashboard import Dashboard

logger = logging.getLogger("main")

HISTORY_SAVE_INTERVAL = 300  # seconds
CALL_TIMEOUT = 60  # seconds a dashboard request waits for the main loop

LOGO = r"""
    __  ___ _
   /  |/  /(_)____ ___   ____   _____ ____ _
  / /|_/ // // __ `__ \ / __ \ / ___// __ `/
 / /  / // // / / / / // /_/ /(__  )/ /_/ /
/_/  /_//_//_/ /_/ /_/ \____//____/ \__,_/
  An AIO Clawer/Monitor/MsgPush Framework
"""

# command -> (Worker method, argument names, description); exit and help are handled in run_command
COMMANDS = {
    "exit": (None, [], "Exit the program"),
    "help": (None, [], "Show this help"),
    "reload": (Worker.reload, [], "Reload modules and task file"),
    "start": (Worker.start_task, ["task"], "Start the task"),
    "stop": (Worker.stop_task, ["task"], "Stop the task"),
    "clear": (Worker.clear_history, ["task"], "Clear history data of the task"),
    "save": (Worker.save_history, [], "Save the history to file"),
}


def command_usage(name):
    return " ".join([name] + ["<{}>".format(arg) for arg in COMMANDS[name][1]])


def run_command(worker, line):
    """ Run a command line, return False when the program should exit """
    words = line.split()
    if not words:
        return True
    name, args = words[0], words[1:]
    if name not in COMMANDS:
        logger.error("Unknown command: {}. Type help for commands.".format(name))
        return True
    method, arg_names, _ = COMMANDS[name]
    if len(args) != len(arg_names):
        logger.error("Usage: {}".format(command_usage(name)))
    elif name == "exit":
        return False
    elif name == "help":
        for cmd, (_, _, description) in COMMANDS.items():
            print("{:<16}{}".format(command_usage(cmd), description))
    else:
        method(worker, *args)
    return True


def read_commands(commands):
    """ Forward stdin lines to the command queue """
    while True:
        try:
            commands.put(input())
        except EOFError:
            # no stdin (e.g. running in background), keep running without commands
            return


class MainLoopClient():
    """ Lets other threads (the dashboard) run something with the worker in the main loop and wait for the result """
    def __init__(self, commands) -> None:
        self.commands = commands

    def call(self, func):
        """ Run func(worker) in the main loop, return its result or raise its exception """
        future = Future()
        self.commands.put((func, future))
        return future.result(timeout=CALL_TIMEOUT)


def run_call(worker, func, future):
    try:
        future.set_result(func(worker))
    except Exception as e:
        future.set_exception(e)


def main_loop(worker, commands):
    """ Everything touching the worker runs here: command lines from stdin and calls from the dashboard """
    last_save = time.time()
    while True:
        try:
            item = commands.get(timeout=0.5)
        except queue.Empty:
            pass
        else:
            if isinstance(item, str):
                if not run_command(worker, item):
                    return
            else:
                run_call(worker, *item)
        worker.schedule()
        if time.time() - last_save >= HISTORY_SAVE_INTERVAL:
            worker.save_history()
            last_save = time.time()


def prepare_files():
    """ Create the external module folders and an empty task file if they are missing """
    external_module_folder = cfg.get_value("EXTERNAL_MODULE_FOLDER", "")
    if external_module_folder:
        for sub_folder in ["source", "data", "renderer", "push"]:
            os.makedirs(os.path.join(external_module_folder, sub_folder), exist_ok=True)
    task_file = cfg.get_value("TASK_FILE", "tasks.json")
    if not os.path.exists(task_file):
        if os.path.dirname(task_file):
            os.makedirs(os.path.dirname(task_file), exist_ok=True)
        with open(task_file, "w", encoding="utf-8") as f:
            f.write("[]")
        logger.info("Created empty task file: {}.".format(task_file))


def main():
    print(LOGO)
    log.setup()
    cfg._init()
    cfg.load_config()
    log.setup(cfg.get_value("LOG_LEVEL", 0))
    prepare_files()

    worker = Worker()
    # stop gracefully on SIGTERM (e.g. docker stop) the same way as Ctrl+C
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    commands = queue.Queue()
    threading.Thread(target=read_commands, args=(commands,), daemon=True).start()
    web = None
    if cfg.get_value("DASHBOARD", False):
        web = Dashboard(MainLoopClient(commands))
        web.start()
    logger.info("Main loop started.")
    try:
        main_loop(worker, commands)
    except KeyboardInterrupt:
        pass
    logger.info("Stopping.")
    if web:
        web.stop()
    worker.shutdown()


if __name__ == "__main__":
    main()
