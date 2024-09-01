import json
import logging

import requests

"""
API module


https://sc2pulse.nephest.com/sc2/doc/swagger-ui/index.html
"""

API_ROOT = "https://sc2pulse.nephest.com/sc2/api"


def get(endpoint):
    logging.info(f"Sending GET request to {endpoint}")
    return requests.get(endpoint)


def get_character_summary(id, depth):
    """
    /character/{id}/summary/1v1/{depth}
    """
    endpoint = API_ROOT + f"/character/{id}/summary/1v1/{depth}"
    return json.loads(get(endpoint).text)


def get_character_search(name):
    """
    "/character/search?term={name}"
    """
    endpoint = API_ROOT + f"/character/search?term={name}"
    return json.loads(get(endpoint).text)


def get_character_common(id, query=""):
    """
    "/character/{id}/common"
    """
    endpoint = API_ROOT + f"/character/{id}/common"
    endpoint = endpoint + query if query else endpoint
    return json.loads(get(endpoint).text)


def get_matches(id, date, matchType="_1V1"):
    """
    /character/{id}/matches/{date}/{matchType}/1/1/1"
    """
    endpoint = API_ROOT + f"/character/{id}/matches/{date}/{matchType}/1/1/1"
    return json.loads(get(endpoint).text)
