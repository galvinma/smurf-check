import logging
from dataclasses import dataclass
from itertools import product
from typing import Any, Optional

from more_itertools import one

from app.api import get_character_common, get_character_search, get_character_summary
from app.static import MATCH_COUNT, PROFILES_DIR
from app.utils.file_utils import write_json


@dataclass
class Player:
    character_id: Optional[str] = None
    name: Optional[str] = None
    race: Optional[str] = None
    region: Optional[str] = None
    realm: Optional[str] = None
    rating_avg: Optional[int] = None
    rating_max: Optional[int] = None
    rating_last: Optional[int] = None
    matches: Optional[Any] = None
    stats: Optional[Any] = None
    mmr_plot_path: Optional[str] = None


GAMES_PLAYED_MAP = {
    "RANDOM": "randomGamesPlayed",
    "ZERG": "zergGamesPlayed",
    "TERRAN": "terranGamesPlayed",
    "PROTOSS": "protossGamesPlayed",
}


def player_from_character_id(character_id, name=None, race=None):
    data = get_character_common(character_id, query="?matchType=_1V1")
    write_json(data=data, path=PROFILES_DIR / f"common/{character_id}.json")
    profile = data["linkedDistinctCharacters"][0]  # TODO This is really a guess.
    members = profile["members"]
    character = members["character"]

    name = character["name"] if name is None else name
    region = character["region"]
    race = one([race for race in GAMES_PLAYED_MAP if GAMES_PLAYED_MAP[race] in members]) if race is None else race
    rating_max = profile["ratingMax"]
    rating_last = profile["currentStats"]["rating"]
    return Player(
        character_id=str(character_id),
        name=name,
        race=race,
        rating_max=rating_max,
        rating_last=rating_last,
        region=region,
    )


def player_from_summary(character_id, name, race, region, depth=MATCH_COUNT):
    data = get_character_summary(character_id, depth=depth)
    write_json(data=data, path=PROFILES_DIR / f"summary/{character_id}.json")
    if len(data) == 1:
        profile = data[0]
    else:
        profile_by_race = {}
        for character in data:
            profile_by_race[character["race"]] = character
        profile = profile_by_race[race]

    return Player(
        character_id=str(character_id),
        name=name,
        race=race,
        rating_avg=profile.get("ratingAvg"),
        rating_max=profile.get("ratingMax"),
        rating_last=profile.get("ratingLast"),
        region=region,
    )


def player_from_character_search(name, race=None, region=None, comparision_mmr=None):
    all_profiles = get_character_search(name)
    write_json(data=all_profiles, path=f"profiles/search/{name}.json")

    def _filter_on_name(name, profiles):
        return [profile for profile in profiles if name in profile["members"]["character"]["name"]]

    def _filter_on_race(race, profiles):
        return [profile for profile in profiles if GAMES_PLAYED_MAP[race] in profile["members"]]

    def _filter_on_region(region, profiles):
        return [profile for profile in profiles if region == profile["members"]["character"]["region"]]

    def _sort_on_mmr(my_mmr, profiles):
        return sorted(
            profiles,
            key=lambda profile: abs(
                profile["currentStats"]["rating"] - my_mmr if profile["currentStats"]["rating"] else 100000
            ),
        )

    def _player_from_name_search(name, race, profile):
        return Player(
            character_id=str(profile["members"]["character"]["id"]),
            name=name,
            race=race,
            rating_last=profile["currentStats"]["rating"],
            rating_max=profile["ratingMax"],
            region=profile["members"]["character"]["region"],
        )

    try:
        logging.info(f"Initially have {len(all_profiles)} profiles.")

        profiles = _filter_on_name(name, all_profiles)
        logging.info(f"After filtering on name we have {len(profiles)} profiles.")
        if len(profiles) == 1:
            return _player_from_name_search(name, race, profiles[0])

        if race:
            profiles = _filter_on_race(race, profiles)
            logging.info(f"After filtering on race we have {len(profiles)} profiles.")
            if len(profiles) == 1:
                return _player_from_name_search(name, race, profiles[0])

            if not profiles:
                logging.info("Adding back in profiles because race filter removed all.")
                profiles = _filter_on_name(name, all_profiles)

        if region:
            profiles = _filter_on_region(region, profiles)
            logging.info(f"After filtering on region we have {len(profiles)} profiles.")
            if len(profiles) == 1:
                return _player_from_name_search(name, race, profiles[0])

        if comparision_mmr:
            profiles = _sort_on_mmr(comparision_mmr, profiles)

        return _player_from_name_search(name, race, profiles[0])
    except Exception as e:
        logging.error("Exception thrown parsing player profile")
        logging.exception(e)
        return None


def player_from_alternate_names(name, race, region, rating_last):
    """
    Find alternative profiles for profiles with l/I
    """
    logging.info("Attempting to locate profile using permuations of 'l' and 'I'")
    logging.info(f"{name=}, {race=}, {region=}, {rating_last=}")

    if not name:
        logging.warning("No name provieded. Unable to find alternates")
        return None

    def _get_sims(s):
        similarities = [["i", "l", "I"]]
        if "!" in s:
            s = s.replace("!", "l")

        perms_limit = 5
        sims = {x: y for y in similarities for x in y}
        idxes = [i for i, x in enumerate(s) if x in sims]
        if len(idxes) > perms_limit:
            return []

        pools = [sims[x] for i, x in enumerate(s) if i in idxes]
        for arrangement in product(*pools):
            L = list(s)
            for i, x in zip(idxes, arrangement):
                L[i] = x
            yield "".join(L)

    alternate_names = list(_get_sims(name))
    if alternate_names:
        logging.info(f"Trying the following alternate names: {alternate_names}")
        for name_perm in alternate_names:
            profile = player_from_character_search(name_perm, race, region, rating_last)
            if profile is not None:
                return profile
    else:
        logging.info("Unable to find alternative names!")
        return None
