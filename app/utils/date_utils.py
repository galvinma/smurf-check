from datetime import datetime

DEFUALT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def timestamp(format="%Y_%m_%d_%H_%M_%S"):
    return datetime.now().strftime(format)
