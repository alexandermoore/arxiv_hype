from datetime import datetime

ISO_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"

def datetime_to_iso(dt):
    return dt.strftime(ISO_FMT)

def iso_to_datetime(iso):
    return datetime.strptime(iso, ISO_FMT)

def maybe_date_str_to_datetime(date_string):
    if date_string is None:
        return None
    try:
        return datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        return None

def datetime_to_date_str(dt):
    return dt.strftime("%Y-%m-%d")