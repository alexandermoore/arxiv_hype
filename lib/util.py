from datetime import datetime

def datetime_to_iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")