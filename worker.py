import os
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


class Worker():
    """ Holds tasks and their history, runs due tasks in a thread pool """
    def __init__(self) -> None:
        self.pipeline = Pipeline()
        self.tasks = {}
        self.history = {}  # task name -> {"time": last run timestamp, "data": last parsed data}
        self.running_tasks = {}  # task name -> Future of its latest run
        self.next_runs = {}  # task name -> (last run time, next run time), cache of next_run_time
        self.executor = ThreadPoolExecutor(max_workers=cfg.get_value("MAX_WORKERS", 8), thread_name_prefix="task")
        self.load_tasks()
        self.load_history()

    # Tasks

    def load_tasks(self):
        """ Load tasks from the task file """
        task_file = cfg.get_value("TASK_FILE", "tasks.json")
        if not os.path.exists(task_file):
            logger.error("No task config file.")
            return
        with open(task_file, "r", encoding="utf-8") as f:
            try:
                task_list = json.load(f)
            except ValueError:
                logger.error("Invalid task config file.")
                return

        self.tasks = {}
        self.next_runs = {}
        for task in task_list:
            if task.get("type") != "static":
                logger.error("Unsupported task type: {} ({}).".format(task.get("type"), task.get("name")))
            elif not all(field in task for field in TASK_FIELDS):
                logger.error("Invalid static task: {}.".format(task.get("name")))
            elif ("cron" in task) == ("interval" in task):
                logger.error("Task needs exactly one of cron and interval: {}.".format(task["name"]))
            else:
                try:
                    next_run_time(task, time.time())
                except (CronSimError, TypeError, AttributeError) as e:
                    logger.error("Invalid schedule of task {}: {}.".format(task["name"], e))
                    continue
                task.setdefault("running", True)
                self.tasks[task["name"]] = task
                logger.info("Static task loaded: {}.".format(task["name"]))

    def start_task(self, name):
        self.set_task_running(name, True)

    def stop_task(self, name):
        self.set_task_running(name, False)

    def set_task_running(self, name, running):
        if name not in self.tasks:
            logger.error("No such task: {}.".format(name))
            return
        self.tasks[name]["running"] = running
        logger.info("Task is {}: {}.".format("started" if running else "stopped", name))

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
        if name not in self.tasks:
            logger.error("No such task: {}.".format(name))
            return
        self.history[name] = self.initial_history(name)
        logger.info("Clear history: {}.".format(name))

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
        history["data"] = self.pipeline.run(task, history["data"])

    def on_task_done(self, name, future):
        if not future.cancelled() and future.exception() is not None:
            exc = future.exception()
            logger.error("Task failed, history kept: {}: {}: {}".format(name, type(exc).__name__, exc))

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
