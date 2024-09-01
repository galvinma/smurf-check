import logging
from dataclasses import dataclass
from typing import Dict, Optional

from more_itertools import one

from app.api import get_matches
from app.player import GAMES_PLAYED_MAP, Player
from app.static import MATCH_COUNT, MIN_MATCH_DURATION
from app.utils.date_utils import DEFUALT_DATE_FORMAT, timestamp
from app.utils.file_utils import write_json
from app.utils.math_utils import average


@dataclass
class Match:
    player: Player
    opponent: Player
    date: str
    duration: str
    map: str
    result: str
    type: str
    participants: Optional[Dict] = None


@dataclass
class MatchStats:
    mmr_delta: int
    match_count: int
    win_count: int
    loss_count: int
    smurf_loss_count: float
    smurf_win_count: float
    win_percent: float
    smurf_loss_percent: float
    smurf_win_percent: float
    smurf_win_loss_ratio: float
    avg_loss_duration: float
    avg_win_duration: float
    avg_duration_ratio: float
    same_race_games_count: int
    same_race_win_count: int
    same_race_loss_count: int
    same_race_win_percent: float
    same_race_loss_percent: float
    smurf_score: float
    smurf_qual: str


def get_matches_for_profile(profile, matchType="_1V1", match_count=MATCH_COUNT):
    date = timestamp(format=DEFUALT_DATE_FORMAT)
    matches = []
    stale_count = 0
    while len(matches) < match_count and stale_count <= 4:
        logging.info(f"Getting matches starting from {date=}")
        data = get_matches(profile.character_id, date=date, matchType=matchType)
        write_json(data=data, path=f"profiles/matches/{profile.character_id}.json", mode="a")

        result = data.get("result", [])

        potential_matches = []
        # NOTE: Append all matches to potential matches!
        # We need the dates from recent invalid matches to search for more potentials
        for match in result:
            try:
                player_id = profile.character_id
                participants = get_match_participants(match)

                result = participants[player_id]["participant"]["decision"]
                type = match["match"]["type"]
                date = match["match"]["date"]
                duration = match["match"]["duration"] if match["match"]["duration"] is not None else 0
                map = match["map"]["name"]
                player_mmr = participants[player_id]["team"]["rating"] if participants[player_id]["team"] else None

                try:
                    opponent_id = str(one(list(filter(lambda x: str(x) != str(player_id), list(participants)))))
                except Exception:
                    opponent_id = None

                opponent_team = participants[opponent_id]["team"] if opponent_id else None
                opponent_mmr = opponent_team["rating"] if opponent_team and opponent_id else None
                opponent_members = opponent_team["members"] if opponent_team and opponent_id else None
                opponent_characters = {}
                if opponent_members:
                    for member in opponent_members:
                        character_id = str(member["character"]["id"])
                        opponent_characters[character_id] = member

                opponent_character = opponent_characters[opponent_id] if opponent_id in opponent_characters else None
                opponent_name = opponent_character["character"]["name"] if opponent_id in opponent_characters else None

                try:
                    opponent_race = (
                        one([race for race in GAMES_PLAYED_MAP if GAMES_PLAYED_MAP[race] in opponent_character])
                        if opponent_id in opponent_characters and opponent_character
                        else None
                    )
                except Exception:
                    opponent_race = None
                    logging.debug("Exception thrown parsing opponent Race")

                potential_matches.append(
                    Match(
                        player=Player(
                            character_id=player_id, name=profile.name, race=profile.race, rating_last=player_mmr
                        ),
                        opponent=Player(
                            character_id=opponent_id,
                            name=opponent_name,
                            race=opponent_race,
                            rating_last=opponent_mmr,
                        ),
                        date=date,
                        duration=duration,
                        map=map,
                        result=result,
                        type=type,
                        participants=participants,
                    )
                )
            except Exception as e:
                logging.error("Exception thrown parsing match")
                logging.exception(f"{match=}")
                raise e

        if potential_matches:
            date = potential_matches[-1].date  # Set date to last game in set for next iteration API call

            # API doesn't seem to respect match_type param. Purge them here
            potential_matches = list(filter(lambda match: match.type == "_1V1", potential_matches))

            # Filter out games with more than two participants
            potential_matches = list(filter(lambda match: len(match.participants) <= 2, potential_matches))

            matches = matches + potential_matches
        else:
            # TODO Work on logic to try another date
            stale_count += 1

    logging.info(f"Found {len(matches)} matches for {profile.name}.")
    return matches


def get_smurf_score(mmr_delta, smurf_win_loss_ratio, avg_duration_ratio, smurf_loss_percent, same_race_loss_percent):
    """
    5 categories for smurfing:
        1. MMR delta
        2. Smurf games (< 60s) win:loss ratio
        3. Duration ratio
        4. Smurf loss % (losses < 60s / total losses)
        5. Same race loss % (same race losses / total losses)

    0:2 Unlikely smurf
    2:2.5 Possible Smurf
    2.5:3.5 Likely Smurf
    >3.5 Definitely Smurf

    Missing a category counts as quarter a point
    """
    count = 0
    logging.debug("Starting smurf check...")

    if mmr_delta:
        if mmr_delta <= 300:
            count += 0
        elif 300 < mmr_delta < 500:
            count += 0.5
        else:
            count += 1
    else:
        count += 0.25
    logging.debug(f"After MMR Delta {count=}")

    if smurf_win_loss_ratio:
        if smurf_win_loss_ratio >= 0.95:
            count += 0
        elif 0.75 < smurf_win_loss_ratio < 0.95:
            count += 0.5
        else:
            count += 1
    else:
        count += 0.25
    logging.debug(f"After Smurf games (< 60s) win:loss ratio {count=}")

    if avg_duration_ratio:
        if avg_duration_ratio <= 1.3:
            count += 0
        elif 1.3 < avg_duration_ratio < 1.7:
            count += 0.5
        else:
            count += 1
    else:
        count += 0.25
    logging.debug(f"After Duration ratio {count=}")

    if smurf_loss_percent:
        if smurf_loss_percent < 10:
            count += 0
        elif 10 < smurf_loss_percent < 17.5:
            count += 0.5
        else:
            count += 1
    else:
        count += 0.25

    logging.debug(f"After smurf loss % {count=}")

    if same_race_loss_percent:
        if same_race_loss_percent <= 60:
            count += 0
        elif 60 < same_race_loss_percent < 70:
            count += 0.5
        else:
            count += 1
    else:
        count += 0.25
    logging.debug(f"After same race loss % {count=}")

    def _qual(count):
        if count < 2:
            return "Unlikely"
        elif 2 <= count < 2.75:
            return "Possible"
        elif 2.75 <= count <= 3.5:
            return "Likely"
        else:
            return "Definitely"

    qual = _qual(count)
    logging.info(f"Smurf check: {count=}, {qual=}")
    return count, qual


def empty_match_stats():
    return MatchStats(
        match_count=None,
        win_count=None,
        loss_count=None,
        smurf_loss_count=None,
        smurf_win_count=None,
        win_percent=None,
        smurf_loss_percent=None,
        smurf_win_percent=None,
        smurf_win_loss_ratio=None,
        avg_loss_duration=None,
        avg_win_duration=None,
        avg_duration_ratio=None,
        same_race_games_count=None,
        same_race_win_count=None,
        same_race_loss_count=None,
        same_race_win_percent=None,
        same_race_loss_percent=None,
        mmr_delta=None,
        smurf_score=None,
        smurf_qual=None,
    )


def get_match_stats(player):
    matches = player.matches
    if len(matches) == 0:
        logging.warning("Received zero matches!")
        return empty_match_stats()

    match_count = len(matches)
    losses = [match for match in matches if match.result == "LOSS"]
    loss_count = len(losses)
    wins = [match for match in matches if match.result == "WIN"]
    win_count = len(wins)

    win_percent = round(win_count / match_count * 100) if match_count else None


    avg_loss_duration = round(average([match.duration for match in losses])) if losses else None
    avg_win_duration = round(average([match.duration for match in wins])) if wins else None
    avg_duration_ratio = round(avg_win_duration / avg_loss_duration, 2) if avg_loss_duration and avg_win_duration else None

    logging.info(f"{len(losses)} Losses, {len(wins)} Wins")

    smurf_wins = [match for match in wins if match.duration is None or match.duration < MIN_MATCH_DURATION]
    smurf_win_count = len(smurf_wins)
    smurf_win_percent = round(smurf_win_count / win_count * 100) if win_count != 0 else None
    logging.info(f"{len(smurf_wins)} wins less than a {MIN_MATCH_DURATION}s")
    logging.info(f"{smurf_win_percent}% of wins are less than {MIN_MATCH_DURATION}s")

    smurf_losses = [match for match in losses if match.duration is None or match.duration < MIN_MATCH_DURATION]
    smurf_loss_count = len(smurf_losses)
    smurf_loss_percent = round(smurf_loss_count / loss_count * 100) if loss_count != 0 else None
    logging.info(f"{len(smurf_losses)} losses less than a {MIN_MATCH_DURATION}s")
    if smurf_loss_percent is not None:
        logging.info(f"{round(smurf_loss_percent)}% of losses are less than {MIN_MATCH_DURATION}s")

    smurf_win_loss_ratio = round(smurf_win_count / smurf_loss_count, 2) if smurf_loss_count != 0 else None

    # Same race losses / wins
    same_race_games = [match for match in matches if match.player.race == match.opponent.race]
    same_race_games_count = len(same_race_games)
    same_race_wins = [match for match in matches if match.result == "WIN" and match.player.race == match.opponent.race]
    same_race_win_count = len(same_race_wins)
    same_race_win_percent = (
        round(same_race_win_count / same_race_games_count * 100) if same_race_games_count != 0 else None
    )

    same_race_losses = [
        match for match in matches if match.result == "LOSS" and match.player.race == match.opponent.race
    ]
    same_race_loss_count = len(same_race_losses)
    same_race_loss_percent = (
        round(same_race_loss_count / same_race_games_count * 100) if same_race_games_count != 0 else None
    )

    mmr_delta = player.rating_max - player.rating_last if player.rating_max and player.rating_last else None
    smurf_score, smurf_qual = get_smurf_score(
        mmr_delta, smurf_win_loss_ratio, avg_duration_ratio, smurf_loss_percent, same_race_loss_percent
    )

    return MatchStats(
        match_count=match_count,
        win_count=win_count,
        loss_count=loss_count,
        smurf_loss_count=smurf_loss_count,
        smurf_win_count=smurf_win_count,
        win_percent=win_percent,
        smurf_loss_percent=smurf_loss_percent,
        smurf_win_percent=smurf_win_percent,
        smurf_win_loss_ratio=smurf_win_loss_ratio,
        avg_loss_duration=avg_loss_duration,
        avg_win_duration=avg_win_duration,
        avg_duration_ratio=avg_duration_ratio,
        same_race_games_count=same_race_games_count,
        same_race_win_count=same_race_win_count,
        same_race_loss_count=same_race_loss_count,
        same_race_win_percent=same_race_win_percent,
        same_race_loss_percent=same_race_loss_percent,
        mmr_delta=mmr_delta,
        smurf_score=smurf_score,
        smurf_qual=smurf_qual,
    )


def get_match_participants(match):
    participants = {}
    for participant in match["participants"]:
        participants[str(participant["participant"]["playerCharacterId"])] = participant

    return participants
