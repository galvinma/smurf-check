import logging
from dataclasses import dataclass

import cv2
import cv2 as cv
import numpy as np
import pytesseract
from more_itertools import one
from PIL import Image

from app.race import Race
from app.static import (
    BARCODE_TEMPLATE_PATH,
    MY_PROFILE_NAME,
    MY_RACE,
    NAMES_DIR,
    PROTOSS_TEMPLATE_PATH,
    RANDOM_TEMPLATE_PATH,
    SCREENSHOTS_DIR,
    TERRAN_TEMPLATE_PATH,
    TMP_DIR,
    ZERG_TEMPLATE_PATH,
)
from app.utils.date_utils import timestamp
from app.utils.file_utils import copy


@dataclass(frozen=True)
class Coordinate:
    top: int
    left: int
    right: int
    bottom: int


TEMPLATE_MATCH_THRESHOLD = 0.75

LEFT_NAME_COORDINATE = Coordinate(left=250, top=440, right=500, bottom=470)
RIGHT_NAME_COORDINATE = Coordinate(left=1920 - 500, top=440, right=1920 - 250, bottom=470)

LEFT_RACE_COORDINATE = Coordinate(left=510, top=440, right=570, bottom=490)
RIGHT_RACE_COORDINATE = Coordinate(left=1920 - 570, top=440, right=1920 - 510, bottom=490)


def screenshot_workflow(screenshot_path):
    # Barcode check
    # TODO Use smaller barcode template image
    is_barcode = barcode_check(screenshot_path)
    if is_barcode:
        logging.warning("You are playing a barcode player!")
        return None, None

    # Crop screenshot
    left_name_path, right_name_path, left_race_path, right_race_path = crop_screenshot(
        screenshot_path, output_dir=TMP_DIR
    )

    # Profile name capture
    left_name = name_capture(left_name_path)
    right_name = name_capture(right_name_path)

    copy(left_name_path, NAMES_DIR / f"{left_name}.png")
    copy(right_name_path, NAMES_DIR / f"{right_name}.png")

    # Race capture
    left_race = race_capture(left_race_path)
    right_race = race_capture(right_race_path)

    logging.info(f"{left_name=}, {left_race=}")
    logging.info(f"{right_name=}. {right_race=}")

    # Copy & rename screenshot
    copy(screenshot_path, SCREENSHOTS_DIR / f"{timestamp()}_{left_name}_{left_race}_{right_name}_{right_race}.png")

    # Detemine opponent details
    opponent_name = [left_name, right_name]
    opponent_name.remove(MY_PROFILE_NAME)
    opponent_name = one(opponent_name)
    opponent_race = [left_race, right_race]
    opponent_race.remove(MY_RACE)
    opponent_race = one(opponent_race)

    logging.info("Done with screenshot parse! ")
    logging.info(f"{opponent_name=}, {opponent_race=}")

    return opponent_name, opponent_race


def crop_screenshot(screenshot_path, output_dir):
    """
    Crop profile names from a screenshot of the versus loading screen
    """

    def _crop_and_save(img, coordinate, output_path):
        crop = img.crop((coordinate.left, coordinate.top, coordinate.right, coordinate.bottom))
        crop.save(output_path)
        return output_path

    img = Image.open(screenshot_path)

    left_name_path = _crop_and_save(img, LEFT_NAME_COORDINATE, f"{output_dir}/left_name.png")
    right_name_path = _crop_and_save(img, RIGHT_NAME_COORDINATE, f"{output_dir}/right_name.png")

    left_race_path = _crop_and_save(img, LEFT_RACE_COORDINATE, f"{output_dir}/left_race.png")
    right_race_path = _crop_and_save(img, RIGHT_RACE_COORDINATE, f"{output_dir}/right_race.png")

    return left_name_path, right_name_path, left_race_path, right_race_path


def template_match(screenshot_path, template_path):
    """
    Return True if template is found in base image
    """
    img_rgb = cv.imread(screenshot_path)
    img_gray = cv.cvtColor(img_rgb, cv.COLOR_BGR2GRAY)
    template = cv.imread(str(template_path), cv.IMREAD_GRAYSCALE)
    res = cv.matchTemplate(img_gray, template, cv.TM_CCOEFF_NORMED)
    loc = np.where(res >= TEMPLATE_MATCH_THRESHOLD)
    try:
        above_threshold = loc[0]
        return True if len(above_threshold) > 0 else False
    except Exception as e:
        logging.exception(e)


def barcode_check(screenshot_path):
    """
    Determine if opponent is barcode from a screenshot of the versus loading screen
    """
    return template_match(screenshot_path, BARCODE_TEMPLATE_PATH)


def name_capture(input_path, rect_size=20):
    """
    Capture the profile name from the cropped screenshot

    https://stackoverflow.com/questions/9480013/image-processing-to-improve-tesseract-ocr-accuracy
    ^ Resize and other options

    https://stackoverflow.com/questions/44619077/pytesseract-ocr-multiple-config-options
    Page segmentation modes:
    0    Orientation and script detection (OSD) only.
    1    Automatic page segmentation with OSD.
    2    Automatic page segmentation, but no OSD, or OCR.
    3    Fully automatic page segmentation, but no OSD. (Default)
    4    Assume a single column of text of variable sizes.
    5    Assume a single uniform block of vertically aligned text.
    6    Assume a single uniform block of text.
    7    Treat the image as a single text line.
    8    Treat the image as a single word.
    9    Treat the image as a single word in a circle.
    10    Treat the image as a single character.
    11    Sparse text. Find as much text as possible in no particular order.
    12    Sparse text with OSD.
    13    Raw line. Treat the image as a single text line,
                            bypassing hacks that are Tesseract-specific.

    """
    logging.info(f"Using {rect_size=} to parse name from image...")
    img = cv2.imread(input_path)
    img = cv2.resize(img, None, fx=1.2, fy=1.2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)
    rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (rect_size, rect_size))
    dilation = cv2.dilate(thresh1, rect_kernel, iterations=1)
    contours, _ = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    img_copy = img.copy()
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        cropped = img_copy[y : y + h, x : x + w]  # noqa: E203
        text = pytesseract.image_to_string(cropped, lang="eng", config="--oem 1 --psm 7").strip()
        if text:
            logging.info(f"Found {text=}")
            if " " in text:
                text = text.split(" ")[-1]
            return text


def race_capture(input_path):
    if template_match(input_path, ZERG_TEMPLATE_PATH):
        return Race.ZERG.value
    elif template_match(input_path, TERRAN_TEMPLATE_PATH):
        return Race.TERRAN.value
    elif template_match(input_path, PROTOSS_TEMPLATE_PATH):
        return Race.PROTOSS.value
    elif template_match(input_path, RANDOM_TEMPLATE_PATH):
        return Race.RANDOM.value
