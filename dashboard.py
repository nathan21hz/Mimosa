import os
import hmac
import json
import logging
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError

from flask import Flask, Response, request, send_file
from werkzeug.exceptions import HTTPException
from werkzeug.serving import make_server

import config as cfg
import utils.log as log
from worker import TaskConfigError

logger = logging.getLogger(__name__)

PAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "dashboard.html")


def json_response(data, status=200):
    # task data comes from arbitrary sources, so fall back to str for anything not JSON serializable
    return Response(json.dumps(data, ensure_ascii=False, default=str), status=status, mimetype="application/json")


def error_response(message, status):
    return json_response({"error": message}, status)


class Dashboard():
    """ Web dashboard. All worker access goes through client.call(), which runs it in the main loop thread """
    def __init__(self, client) -> None:
        self.client = client  # main.MainLoopClient
        self.token = cfg.get_value("DASHBOARD_TOKEN", "")
        self.app = Flask(__name__)
        self.app.before_request(self.check_token)
        self.app.register_error_handler(Exception, self.on_error)
        self.app.add_url_rule("/", view_func=self.index)
        self.app.add_url_rule("/api/tasks", view_func=self.get_tasks)
        self.app.add_url_rule("/api/tasks", view_func=self.add_task, methods=["POST"])
        self.app.add_url_rule("/api/tasks/<name>/start", view_func=self.start_task, methods=["POST"])
        self.app.add_url_rule("/api/tasks/<name>/stop", view_func=self.stop_task, methods=["POST"])
        self.app.add_url_rule("/api/tasks/<name>/clear", view_func=self.clear_history, methods=["POST"])
        self.app.add_url_rule("/api/tasks/<name>/config", view_func=self.get_task_config)
        self.app.add_url_rule("/api/tasks/<name>/config", view_func=self.put_task_config, methods=["PUT"])
        self.app.add_url_rule("/api/reload", view_func=self.reload, methods=["POST"])
        self.app.add_url_rule("/api/logs", view_func=self.get_logs)
        host = cfg.get_value("DASHBOARD_HOST", "127.0.0.1")
        port = cfg.get_value("DASHBOARD_PORT", 8080)
        self.server = make_server(host, port, self.app, threaded=True)
        logger.info("Dashboard on http://{}:{}/".format(host, port))

    def start(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()

    def on_error(self, e):
        if isinstance(e, HTTPException):
            return e
        if isinstance(e, FutureTimeoutError):
            return error_response("Main loop is busy, try again later.", 504)
        logger.error("Request failed: {} {}: {!r}".format(request.method, request.path, e))
        return error_response("{}: {}".format(type(e).__name__, e), 500)

    def check_token(self):
        if self.token and request.path.startswith("/api/"):
            if not hmac.compare_digest(request.headers.get("X-Token", ""), self.token):
                return error_response("Invalid token.", 401)

    def index(self):
        return send_file(PAGE_FILE)

    def get_tasks(self):
        return json_response(self.client.call(lambda worker: worker.status()))

    def start_task(self, name):
        return self.task_action(name, lambda worker: worker.start_task(name))

    def stop_task(self, name):
        return self.task_action(name, lambda worker: worker.stop_task(name))

    def clear_history(self, name):
        return self.task_action(name, lambda worker: worker.clear_history(name))

    def task_action(self, name, action):
        if not self.client.call(action):
            return error_response("No such task: {}.".format(name), 404)
        return json_response({})

    def get_task_config(self, name):
        task = self.client.call(lambda worker: worker.read_task_config(name))
        if task is None:
            return error_response("No such task in the task file: {}.".format(name), 404)
        return json_response(task)

    def add_task(self):
        return self.change_task_config(lambda worker, task: worker.add_task_config(task))

    def put_task_config(self, name):
        return self.change_task_config(lambda worker, task: worker.save_task_config(name, task))

    def change_task_config(self, change):
        task = request.get_json(silent=True)
        if task is None:
            return error_response("Request body must be JSON.", 400)
        try:
            self.client.call(lambda worker: change(worker, task))
        except TaskConfigError as e:
            return error_response(str(e), 400)
        return json_response({})

    def reload(self):
        self.client.call(lambda worker: worker.reload())
        return json_response({})

    def get_logs(self):
        return json_response({"logs": log.get_log_record()})
