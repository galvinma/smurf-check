"""
https://pypi.org/project/watchdog/#description
"""

import logging
import os
import time

from dotenv import load_dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.smurf_check import execute_smurf_check

load_dotenv()

WATCH_DIR = os.environ.get("WATCH_DIR")


class CreationHandler(FileSystemEventHandler):
    @staticmethod
    def on_any_event(event):
        if event.event_type == "created":
            logging.info(f"Found new file: {event.src_path=}")
            execute_smurf_check(screenshot_path=event.src_path, open_profile=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    logging.info(f"Starting observer. {WATCH_DIR=}")

    handler = CreationHandler()
    observer = Observer()
    observer.schedule(handler, WATCH_DIR)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
