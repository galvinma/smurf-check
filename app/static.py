import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# My account
MY_PROFILE_NAME = os.environ.get("MY_PROFILE_NAME")
MY_RACE = os.environ.get("MY_RACE")
MY_CHARACTER_ID = os.environ.get("MY_CHARACTER_ID")
MY_REGION = os.environ.get("MY_REGION")

# Flask
STATIC_DIR = Path(os.environ.get("STATIC_DIR"))

# Matches
MATCH_COUNT = 1000  # Maximum number of matches to use in smurf stats
MIN_MATCH_DURATION = 60  # Seconds

# JSON paths
PROFILES_DIR = Path(os.environ.get("PROFILES_DIR"))
MATCHES_DIR = PROFILES_DIR / "matches"

# Image paths
TMP_DIR = Path(os.environ.get("TMP_DIR"))
IMAGES_DIR = Path(os.environ.get("IMAGES_DIR"))
SCREENSHOTS_DIR = IMAGES_DIR / "screenshots"
NAMES_DIR = IMAGES_DIR / "names"
TEMPLATES_DIR = IMAGES_DIR / "templates"
ZERG_TEMPLATE_PATH = TEMPLATES_DIR / "zerg.png"
TERRAN_TEMPLATE_PATH = TEMPLATES_DIR / "terran.png"
PROTOSS_TEMPLATE_PATH = TEMPLATES_DIR / "protoss.png"
RANDOM_TEMPLATE_PATH = TEMPLATES_DIR / "random.png"
BARCODE_TEMPLATE_PATH = TEMPLATES_DIR / "barcode.png"
