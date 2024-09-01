import matplotlib

matplotlib.use("agg")

import logging
from datetime import datetime
import matplotlib.pyplot as plt
from app.static import MATCH_COUNT, STATIC_DIR

# TODO: This shows more than 1v1 games and \
#   it should only show target race


def mmr_plot(player, depth=MATCH_COUNT):
    character_id = player.character_id
    logging.info(f"Creating MMR plot for {character_id=}")
    try:
        outpath = STATIC_DIR / f"mmr_plot/{character_id}.png"
        logging.info(f"Attempting to create MMR plot from {len(player.matches)} matches...")

        dates = []
        ratings = []
        # Isolate only the 1v1 matches of target race
        for match in player.matches:
            date = match.date
            type = match.type

            if type != "_1V1":
                continue

            participants = match.participants
            if len(participants) != 2:
                continue

            if character_id not in participants:
                continue

            team_state = participants[character_id]["teamState"] if "teamState" in participants[character_id] else {}
            team_state = team_state["teamState"] if team_state and "teamState" in team_state else {}
            rating = team_state["rating"] if team_state and "rating" in team_state else None

            if date and rating:
                formatted_date = datetime.strptime(date.split("T")[0], "%Y-%m-%d").date()
                dates.append(formatted_date)
                ratings.append(rating)

        logging.info(f"Found {len(ratings)} matches for MMR plot...")

        fig, ax = plt.subplots(1, figsize=(9, 6))
        ax.grid()
        plt.title("MMR by Date")
        plt.xticks(rotation=90)
        plt.plot(dates, ratings, label="MMR")
        if player.rating_max:
            plt.plot(dates, [player.rating_max for _ in dates], label="Max MMR", color="red")
        plt.savefig(outpath, format="png", bbox_inches="tight")
        return outpath
    except Exception as e:
        logging.error("Exception thrown creating MMR plot...")
        logging.exception(e)
