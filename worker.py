import os
import copy
import json
import time
import pickle
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, wait

from cronsim import CronSim, CronSimError

import config as cfg
from pipeline import Pipeline

logger = logging.getLogger(__name__)

# plus one of "cron" and "interval"
TASK_FIELDS = ["name", "startup_data", "source", "data", "condition", "push"]

# crontab shortcuts, which cronsim does not support
CRON_ALIASES = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}


# earliest start for cron calculation (2000-01-01); local times near the epoch raise OSError on Windows,
# and any older last run is due anyway
MIN_CRON_START = 946684800


def next_run_time(task, last_run):
    """ Timestamp of the first scheduled run after last_run (local time for cron) """
    if "cron" in task:
        expr = CRON_ALIASES.get(task["cron"].strip(), task["cron"])
        start = datetime.fromtimestamp(max(last_run, MIN_CRON_START))
        return next(CronSim(expr, start)).timestamp()
    return last_run + task["interval"]


def validate_task(task):
    """ Return why the task config is invalid, or None if it is valid """
    if not isinstance(task, dict):
        return "Task must be a JSON object."
    if task.get("type") != "static":
        return "Unsupported task type: {}.".format(task.get("type"))
    missing = [field for field in TASK_FIELDS if field not in task]
    if missing:
        return "Missing fields: {}.".format(", ".join(missing))
    if not isinstance(task["name"], str) or not task["name"]:
        return "Task name must be a non-empty string."
    if ("cron" in task) == ("interval" in task):
        return "Task needs exactly one of cron and interval."
    try:
        next_run_time(task, time.time())
    except (CronSimError, TypeError, AttributeError) as e:
        return "Invalid schedule: {}.".format(e)
    return None


class TaskConfigError(Exception):
    """ A task config from the user can't be saved """


class Worker():
    """ Holds tasks and their history, runs due tasks in a thread pool """
    def __init__(self) -> None:
        self.pipeline = Pipeline()
        self.tasks = {}
        self.invalid_tasks = {}  # task name -> why it is not loaded
        self.history = {}  # task name -> {"time": last run timestamp, "data": last parsed data}
        self.running_tasks = {}  # task name -> Future of its latest run
        self.next_runs = {}  # task name -> (last run time, next run time), cache of next_run_time
        self.results = {}  # task name -> result of its latest finished run
        self.executor = ThreadPoolExecutor(max_workers=cfg.get_value("MAX_WORKERS", 8), thread_name_prefix="task")
        self.load_tasks()
        self.load_history()

    # Tasks

    def task_file(self):
        return cfg.get_value("TASK_FILE", "tasks.json")

    def read_task_file(self):
        """ Task list in the task file, raise OSError / ValueError if it can't be read """
        with open(self.task_file(), "r", encoding="utf-8") as f:
            task_list = json.load(f)
        if not isinstance(task_list, list):
            raise ValueError("Task file must be a JSON list.")
        return task_list

    def write_task_file(self, task_list):
        """ Write the task list, through a temp file so a failed write won't break the task file """
        tmp_file = self.task_file() + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(task_list, f, indent=4, ensure_ascii=False)
        os.replace(tmp_file, self.task_file())

    def load_tasks(self):
        """ Load tasks from the task file """
        try:
            task_list = self.read_task_file()
        except FileNotFoundError:
            logger.error("No task config file.")
            return
        except (OSError, ValueError) as e:
            logger.error("Invalid task config file: {}".format(e))
            return

        self.tasks = {}
        self.invalid_tasks = {}
        self.next_runs = {}
        for task in task_list:
            error = validate_task(task)
            if error:
                name = task.get("name") if isinstance(task, dict) else None
                logger.error("Invalid task {}: {}".format(name, error))
                if isinstance(name, str) and name:
                    self.invalid_tasks[name] = error
                continue
            task.setdefault("running", True)
            self.tasks[task["name"]] = task
            logger.info("Static task loaded: {}.".format(task["name"]))

    def read_task_config(self, name):
        """ Config of the task as saved in the task file, None if not found """
        for task in self.read_task_file():
            if isinstance(task, dict) and task.get("name") == name:
                return task
        return None

    def save_task_config(self, name, new_task):
        """ Replace the task in the task file and apply it, raise TaskConfigError if it can't be saved """
        error = validate_task(new_task)
        if error:
            raise TaskConfigError(error)
        task_list = self.read_task_file()
        names = [task.get("name") if isinstance(task, dict) else None for task in task_list]
        if name not in names:
            raise TaskConfigError("No such task in the task file: {}.".format(name))
        new_name = new_task["name"]
        if new_name != name and new_name in names:
            raise TaskConfigError("Task name already exists: {}.".format(new_name))
        task_list[names.index(name)] = new_task
        self.write_task_file(task_list)
        logger.info("Task config saved: {}.".format(new_name))
        self.apply_task(name, copy.deepcopy(new_task))

    def add_task_config(self, new_task):
        """ Append a new task to the task file and load it, raise TaskConfigError if it can't be added """
        error = validate_task(new_task)
        if error:
            raise TaskConfigError(error)
        try:
            task_list = self.read_task_file()
        except FileNotFoundError:
            task_list = []
        if any(isinstance(task, dict) and task.get("name") == new_task["name"] for task in task_list):
            raise TaskConfigError("Task name already exists: {}.".format(new_task["name"]))
        task_list.append(new_task)
        self.write_task_file(task_list)
        logger.info("Task added: {}.".format(new_task["name"]))
        task = copy.deepcopy(new_task)
        task.setdefault("running", True)
        self.tasks[task["name"]] = task
        self.history[task["name"]] = self.initial_history(task["name"])

    def apply_task(self, old_name, task):
        """ Replace a loaded task with its new config, keeping its position, history and running state """
        new_name = task["name"]
        old_task = self.tasks.get(old_name)
        if old_task is None:
            # an invalid task got fixed
            self.invalid_tasks.pop(old_name, None)
            task.setdefault("running", True)
            self.tasks[new_name] = task
            self.history[new_name] = self.initial_history(new_name)
        else:
            task.setdefault("running", old_task["running"])
            self.tasks = {new_name if k == old_name else k: task if k == old_name else v for k, v in self.tasks.items()}
            self.history = {new_name if k == old_name else k: v for k, v in self.history.items()}
            if old_name in self.running_tasks:
                self.running_tasks[new_name] = self.running_tasks.pop(old_name)
        self.next_runs.pop(old_name, None)

    def start_task(self, name):
        return self.set_task_running(name, True)

    def stop_task(self, name):
        return self.set_task_running(name, False)

    def set_task_running(self, name, running):
        """ Return False if there is no such task """
        if name not in self.tasks:
            logger.error("No such task: {}.".format(name))
            return False
        self.tasks[name]["running"] = running
        logger.info("Task is {}: {}.".format("started" if running else "stopped", name))
        return True

    # History

    def history_file(self):
        return cfg.get_value("HISTORY_FILE") or "history.pkl"

    def initial_history(self, name):
        return {"time": 0, "data": self.tasks[name]["startup_data"]}

    def load_history(self):
        """ Load history from file, keeping only entries of loaded tasks """
        logger.info("Load history.")
        saved = {}
        if os.path.isfile(self.history_file()):
            with open(self.history_file(), "rb") as f:
                saved = pickle.load(f)
        self.history = {name: saved[name] if name in saved else self.initial_history(name) for name in self.tasks}

    def save_history(self):
        logger.info("Save history to file.")
        with open(self.history_file(), "wb") as f:
            pickle.dump(self.history, f)

    def clear_history(self, name):
        """ Return False if there is no such task """
        if name not in self.tasks:
            logger.error("No such task: {}.".format(name))
            return False
        self.history[name] = self.initial_history(name)
        logger.info("Clear history: {}.".format(name))
        return True

    # Lifecycle

    def reload(self):
        """ Reload modules and tasks """
        logger.info("Reload started.")
        self.wait_running_tasks()
        self.save_history()
        logger.info("Reloading modules.")
        self.pipeline.reload()
        logger.info("Reloading tasks.")
        self.load_tasks()
        self.load_history()
        logger.info("Reload finished.")

    def shutdown(self):
        """ Wait for running tasks, drop queued ones and save history """
        logger.info("Waiting for running tasks.")
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.save_history()

    # Scheduling

    def schedule(self):
        """ Submit due tasks without waiting for them.
        Runs missed while stopped (or before the first run) are caught up with a single run. """
        now = time.time()
        for name, task in self.tasks.items():
            if not task["running"] or self.due_time(name) > now:
                continue
            self.history[name]["time"] = now
            if self.is_task_running(name):
                logger.warning("Previous run still in progress, skipped: {}.".format(name))
                continue
            logger.info("Updating: {}.".format(name))
            self.submit_task(name)

    def due_time(self, name):
        """ Next run time of the task, recomputed only when its last run time changes """
        last_run = self.history[name]["time"]
        cached = self.next_runs.get(name)
        if cached is None or cached[0] != last_run:
            cached = (last_run, next_run_time(self.tasks[name], last_run))
            self.next_runs[name] = cached
        return cached[1]

    def submit_task(self, name):
        future = self.executor.submit(self.run_task, self.tasks[name])
        future.add_done_callback(lambda f: self.on_task_done(name, f))
        self.running_tasks[name] = future

    def run_task(self, task):
        """ Run a task once and keep its data as history, called in the thread pool.
        If fetching fails the pipeline raises, so nothing is pushed and the history is kept. """
        history = self.history[task["name"]]
        history["data"], pushed = self.pipeline.run(task, history["data"])
        self.results[task["name"]] = {"time": time.time(), "ok": True, "pushed": pushed}

    def on_task_done(self, name, future):
        if not future.cancelled() and future.exception() is not None:
            exc = future.exception()
            error = "{}: {}".format(type(exc).__name__, exc)
            self.results[name] = {"time": time.time(), "ok": False, "error": error}
            logger.error("Task failed, history kept: {}: {}".format(name, error))

    def is_task_running(self, name):
        future = self.running_tasks.get(name)
        return future is not None and not future.done()

    def wait_running_tasks(self):
        """ Block until all running tasks finish """
        pending = [f for f in self.running_tasks.values() if not f.done()]
        if pending:
            logger.info("Waiting for {} running task(s).".format(len(pending)))
            wait(pending)
        self.running_tasks = {}

    # Dry run

    def dry_run_context(self, name, task):
        """ Pipeline and history data to dry run a task config with, called in the main loop.
        Uses the current history of the task being edited (name), otherwise the config's startup data. """
        if name in self.history:
            return self.pipeline, copy.deepcopy(self.history[name]["data"]), "current"
        return self.pipeline, copy.deepcopy(task.get("startup_data", [])), "startup"

    # Status

    def status(self):
        """ State of every task, including tasks not loaded because of invalid config """
        now = time.time()
        tasks = []
        for name, task in self.tasks.items():
            tasks.append({
                "name": name,
                "cron": task.get("cron"),
                "interval": task.get("interval"),
                "running": task["running"],
                "busy": self.is_task_running(name),
                "last_run": self.history[name]["time"] or None,
                "next_run": max(self.due_time(name), now) if task["running"] else None,
                "data": self.history[name]["data"],
                "result": self.results.get(name),
            })
        for name, error in self.invalid_tasks.items():
            tasks.append({"name": name, "invalid": error})
        return tasks
