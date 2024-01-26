from datetime import datetime
import os
from dotenv import load_dotenv

ISO_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


def datetime_to_iso(dt):
    return dt.strftime(ISO_FMT)


def iso_to_datetime(iso):
    return datetime.fromisoformat(iso.replace(" ", "T"))
    # return datetime.strptime(iso, ISO_FMT)


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
