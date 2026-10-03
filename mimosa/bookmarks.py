import os
import json
import time
import uuid
import logging
import threading

from mimosa import config as cfg

logger = logging.getLogger(__name__)

# task config sections a bookmark can hold, and the JSON types allowed for each
KINDS = {
    "stage": (dict, list),      # one stage, or the whole stages list
    "source": (dict,),
    "renderer": (dict,),
    "data": (dict, list),       # one data item, or the whole list
    "condition": (dict, list),  # one condition, or the whole list
    "push": (dict, list),       # one channel, or the whole list
}
MAX_NAME_LENGTH = 100


class BookmarkError(Exception):
    """ A bookmark from the user can't be saved """


class BookmarkStore():
    """ Task config snippets saved from the dashboard, kept in a JSON file next to the task file """
    def __init__(self) -> None:
        # requests run in parallel web threads
        self.lock = threading.Lock()

    def file(self):
        task_file = cfg.get_value("TASK_FILE", "tasks.json")
        return cfg.get_value("BOOKMARK_FILE") or os.path.join(os.path.dirname(task_file), "bookmarks.json")

    def read(self):
        if not os.path.exists(self.file()):
            return []
        with open(self.file(), "r", encoding="utf-8") as f:
            return json.load(f)

    def write(self, bookmarks):
        tmp_file = self.file() + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(bookmarks, f, indent=4, ensure_ascii=False)
        os.replace(tmp_file, self.file())

    def list(self):
        with self.lock:
            return self.read()

    def add(self, name, kind, value):
        """ Save a new bookmark and return it, raise BookmarkError if invalid """
        if not isinstance(name, str) or not name.strip():
            raise BookmarkError("Bookmark name must be a non-empty string.")
        if len(name) > MAX_NAME_LENGTH:
            raise BookmarkError("Bookmark name is longer than {} characters.".format(MAX_NAME_LENGTH))
        if kind not in KINDS:
            raise BookmarkError("Unknown bookmark kind: {}.".format(kind))
        if not isinstance(value, KINDS[kind]):
            raise BookmarkError("A {} bookmark must be a JSON {}.".format(
                kind, " or ".join("object" if t is dict else "list" for t in KINDS[kind])))
        bookmark = {"id": uuid.uuid4().hex, "name": name.strip(), "kind": kind, "value": value, "created": time.time()}
        with self.lock:
            bookmarks = self.read()
            bookmarks.append(bookmark)
            self.write(bookmarks)
        logger.info("Bookmark added: {} ({}).".format(bookmark["name"], kind))
        return bookmark

    def delete(self, bookmark_id):
        """ Return False if there is no such bookmark """
        with self.lock:
            bookmarks = self.read()
            kept = [b for b in bookmarks if b.get("id") != bookmark_id]
            if len(kept) == len(bookmarks):
                return False
            self.write(kept)
        logger.info("Bookmark deleted: {}.".format(bookmark_id))
        return True
