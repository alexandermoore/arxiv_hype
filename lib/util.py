from datetime import datetime

ISO_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"

def datetime_to_iso(dt):
    return dt.strftime(ISO_FMT)

def iso_to_datetime(iso):
    return datetime.strptime(iso, ISO_FMT)