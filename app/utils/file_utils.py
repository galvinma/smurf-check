import json
import logging
import shutil
from pathlib import Path

from app.static import PROFILES_DIR


def move(src, dst):
    logging.info(f"Move from {src} to {dst}")
    shutil.move(src, dst)


def copy(src, dst):
    logging.info(f"Copy from {src} to {dst}")
    shutil.copy(src, dst)


def write_json(data, path, mode="w"):
    with open(path, mode, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4, default=str)


def get_player_notes(character_id):
    notes = {}
    if Path(f"{PROFILES_DIR}/notes/{character_id}.json").exists():
        with open(f"{PROFILES_DIR}/notes/{character_id}.json") as f:
            notes = json.load(f)

    return notes
