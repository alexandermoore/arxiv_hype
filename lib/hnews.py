# Hacker news
import requests
from requests.adapters import HTTPAdapter, Retry
from lib import arxiv, util
from typing import List, Optional
from datetime import datetime, timezone
import pydantic
from html2text import html2text
import time
import logging

DATE_SEARCH_URL = "http://hn.algolia.com/api/v1/search_by_date"
POP_SEARCH_URL = "http://hn.algolia.com/api/v1/search"


class HNewsPost(pydantic.BaseModel):
    hnews_id: str = ...
    points: Optional[int] = None
    arxiv_ids: List[str] = ...
    num_comments: Optional[int] = None
    created_at: datetime = ...
    is_story: bool = False
    is_comment: bool = False


def _get_or_else(d, key, default=""):
    r = d.get(key)
    return default if r is None else r


def search_for_arxiv(start_time=None, end_time=None, num_results=10, order_by="date"):
    if order_by == "date":
        search_url = DATE_SEARCH_URL
    elif order_by == "popularity":
        search_url = POP_SEARCH_URL
    else:
        raise ValueError(f"Invalid order_by '{order_by}'")

    date_filter = []
    if start_time:
        start_time = start_time.replace(tzinfo=timezone.utc).timestamp()
        date_filter.append(f"created_at_i>={start_time}")
    if end_time:
        end_time = end_time.replace(tzinfo=timezone.utc).timestamp()
        date_filter.append(f"created_at_i<={end_time}")

    def _search_for_arxiv(page):
        params = {
            "query": "arxiv.org",
            "tags": "(story,comment)",
            "page": page if page > 1 else None,
            "numericFilters": ",".join(date_filter) if len(date_filter) else None,
            "hitsPerPage": min(100, num_results),
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = request_raw(search_url, params)
        hits = response.get("hits")
        results = []
        if hits:
            for hit in hits:
                text = " ".join(
                    [
                        _get_or_else(hit, "url", ""),
                        html2text(_get_or_else(hit, "story_text", "")),
                        html2text(_get_or_else(hit, "comment_text", "")),
                    ]
                )
                arxiv_ids = list(set(arxiv.maybe_text_to_arxiv_ids(text)))
                if not len(arxiv_ids):
                    continue
                tags = _get_or_else(hit, "_tags", [])
                results.append(
                    HNewsPost(
                        hnews_id=hit.get("objectID"),
                        points=hit.get("points"),
                        arxiv_ids=arxiv_ids,
                        num_comments=hit.get("num_comments"),
                        created_at=util.iso_to_datetime(hit.get("created_at")),
                        is_story="story" in tags,
                        is_comment="comment" in tags,
                    )
                )
        return results

    results = []
    i = 0
    while len(results) < num_results:
        i += 1
        new_results = _search_for_arxiv(page=i)
        time.sleep(0.6)  # Keep us well below 10k requests per hour limit
        if not len(new_results):
            break
        results.extend(new_results)
        logging.info(f"Found {len(results)} HN results so far...")
    # deduplicate (shouldn't happen but never know)
    final_results = []
    seen = set()
    for r in results:
        if r.hnews_id not in seen:
            final_results.append(r)
            seen.add(r.hnews_id)
    return final_results[:num_results]


def request_raw(url, params, retries=3):
    """Makes a request to the Hacker News API
    Args:
        url: API endpoint URL
        params: Dict of params
        retries: Number of retries

    Returns:
        Raw response as a dict.
    """
    # with open("private/sample_twitter_response.json", "r") as f:
    #     return json.load(f)
    with requests.Session() as s:
        retries = Retry(
            total=retries, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]
        )
        s.mount("https://", HTTPAdapter(max_retries=retries))
        response = s.get(url, params=params)
    return response.json()
