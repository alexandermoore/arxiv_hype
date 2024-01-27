from datetime import datetime
import os
from dotenv import load_dotenv
import math

ISO_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"

ISO_FMT2 = "%Y-%m-%dT%H:%M:%SZ"

ALT_FMT = "%a %b %d %H:%M:%S %z %Y"


def datetime_to_iso(dt):
    return dt.strftime(ISO_FMT)


def multi_formats_to_datetime(dt_str):
    try:
        dt = iso_to_datetime(dt_str)
    except ValueError:
        dt = datetime.strptime(dt_str, ALT_FMT)
    return dt


def iso_to_datetime(iso):
    # return datetime.fromisoformat(iso)  # .replace(" ", "T"))
    try:
        return datetime.strptime(iso, ISO_FMT)
    except ValueError:
        return datetime.strptime(iso, ISO_FMT2)


def maybe_date_str_to_datetime(date_string):
    if date_string is None:
        return None
    try:
        return datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        return None


def datetime_to_date_str(dt):
    return dt.strftime("%Y-%m-%d")


def get_env_var(name, default=None, must_exist=False):
    variable = os.getenv(name)
    if variable is None:
        if os.path.isfile("private/.env_secrets"):
            load_dotenv(dotenv_path="private/.env_secrets")
        if os.path.isfile("private/.env_local"):
            load_dotenv(dotenv_path="private/.env_local")
        variable = os.getenv(name, default=default)
    if must_exist and variable is None:
        raise NameError(f"Environment variable {name} not found!")
    return variable


def create_intervals(start, end, num_blocks):
    """_summary_
    print(create_intervals(0, 5, 3))   # Output: [(0, 1), (2, 3), (4, 5)]
    print(create_intervals(0, 2, 3))   # Output: [(0, 0), (1, 1), (2, 2)]
    print(create_intervals(0, 10, 3))  # Output: [(0, 3), (4, 7), (8, 10)]
    print(create_intervals(0, 2, 10))  # Output: [(0, 0), (1, 1), (2, 2)]
    """
    block_size = math.ceil((end - start) / num_blocks)
    block_size = int(block_size)
    res = []
    while start <= end and len(res) < num_blocks:
        res.append([start, min(start + block_size - 1, end)])
        start += block_size
    if len(res) == num_blocks:
        res[-1][1] = end
    return res
