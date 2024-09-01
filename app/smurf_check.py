"""
Entrypoint for smurf check
"""

import argparse
import dataclasses
import logging
from time import perf_counter

from dotenv import load_dotenv

from app.browser import open_url
from app.image import screenshot_workflow
from app.matches import get_match_stats, get_matches_for_profile
from app.player import (
    player_from_alternate_names,
    player_from_character_id,
    player_from_character_search,
    player_from_summary,
)
from app.plot import mmr_plot
from app.static import MATCH_COUNT, MY_CHARACTER_ID, MY_PROFILE_NAME, MY_RACE, MY_REGION
from app.utils.file_utils import write_json

load_dotenv()


def execute_smurf_check(
    screenshot_path=None, opponent_character_id=None, opponent_name=None, opponent_race=None, open_profile=False
):
    """
    Calculate smurfing stats given either a loading screenshot or username as input
    """
    start = perf_counter()

    if screenshot_path:
        opponent_name, opponent_race = screenshot_workflow(screenshot_path)
        if opponent_name is None:
            logging.warning(f"Unable to parse opponent details from screenshot.")
            return

    # Profiles
    player = player_from_summary(MY_CHARACTER_ID, MY_PROFILE_NAME, MY_RACE, MY_REGION)

    if opponent_character_id:
        opponent = player_from_character_id(character_id=opponent_character_id, name=opponent_name, race=opponent_race)
    else:
        opponent = player_from_character_search(opponent_name, opponent_race, MY_REGION, player.rating_last)
        if opponent and opponent.character_id:
            opponent = player_from_summary(opponent.character_id, opponent.name, opponent.race, opponent.region)

    # Try barcode iterations if we failed
    if opponent is None:
        logging.warning(f"Unable to get player details for {opponent_name=}")
        opponent = player_from_alternate_names(opponent_name, opponent_race, MY_REGION, player.rating_last)

    logging.info(f"{player=}")
    logging.info(f"{opponent=}")

    # Get stats
    opponent.matches = get_matches_for_profile(opponent, match_count=MATCH_COUNT)
    opponent.mmr_plot_path = mmr_plot(opponent)
    opponent.stats = get_match_stats(opponent)

    write_json(
        data=dataclasses.asdict(opponent),
        path=f"profiles/stats/{opponent.character_id}.json",
        mode="w",
    )

    if open_profile:
        url = f"http://127.0.0.1:5000/profile/{opponent.character_id}"
        logging.info(f"Opening profile. URL={url}")
        open_url(url)

    stop = perf_counter()
    logging.info(f"Smurf check took {round(stop - start, 2)} seconds.")

    return player, opponent


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser()
    parser.add_argument("-opponent_character_id")
    parser.add_argument("-opponent_name")
    parser.add_argument("-opponent_race")
    parser.add_argument("-open_profile", default=False)
    args = parser.parse_args()
    execute_smurf_check(
        opponent_character_id=args.opponent_character_id,
        opponent_name=args.opponent_name,
        opponent_race=args.opponent_race,
        open_profile=args.open_profile,
    )
