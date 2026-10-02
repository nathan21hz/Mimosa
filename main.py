import time
import queue
import logging
import threading

import config as cfg
import utils.log as log
from worker import Worker

logger = logging.getLogger("main")

HISTORY_SAVE_INTERVAL = 300  # seconds

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


def main_loop(worker, commands):
    last_save = time.time()
    while True:
        try:
            line = commands.get(timeout=0.5)
        except queue.Empty:
            pass
        else:
            if not run_command(worker, line):
                return
        worker.schedule()
        if time.time() - last_save >= HISTORY_SAVE_INTERVAL:
            worker.save_history()
            last_save = time.time()


def main():
    print(LOGO)
    log.setup()
    cfg._init()
    cfg.load_config()
    log.setup(cfg.get_value("LOG_LEVEL", 0))

    worker = Worker()
    commands = queue.Queue()
    threading.Thread(target=read_commands, args=(commands,), daemon=True).start()
    logger.info("Main loop started.")
    try:
        main_loop(worker, commands)
    except KeyboardInterrupt:
        pass
    logger.info("Stopping.")
    worker.shutdown()


if __name__ == "__main__":
    main()
