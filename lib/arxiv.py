import arxiv
import pydantic
from typing import List, Optional
import re
from datetime import datetime
from concurrent import futures
import time
import random
import logging

_ARXIV_ID_PATTERN = "[0-9]+\.[0-9]+"

ARXIV_ML_CATEGORIES = "cs.CV,cs.LG,cs.CL,cs.AI,cs.NE,cs.RO,cs.MA,cs.IR".split(",")


class ArxivPaper(pydantic.BaseModel):
    arxiv_id: str = ...
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    categories: Optional[List[str]] = None
    published: Optional[datetime] = None
    updated: Optional[datetime] = None
    embedding: Optional[List] = None

    @property
    def published_ts(self):
        return datetime.strftime("")


def get_paper_info(arxiv_ids):
    results = arxiv.Search(id_list=arxiv_ids, max_results=float("inf")).results()
    return [
        ArxivPaper(
            arxiv_id=arxiv_ids[i],
            title=r.title,
            authors=[a.name for a in r.authors],
            abstract=r.summary,
            categories=r.categories,
            published=r.published,
            embedding=None,
        )
        for i, r in enumerate(results)
    ]


def _get_paper_info_with_sleep(arxiv_ids, sleep):
    sleep = float(sleep)
    time.sleep(sleep * (0.25 + random.random() * 0.50))
    r = get_paper_info(arxiv_ids)
    time.sleep(sleep * (0.25 + random.random() * 0.50))
    return r


def get_paper_info_parallel(arxiv_ids, max_per_request=50, max_workers=3, sleep=5):
    results = []
    failed_ids = []
    with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {}
        for i in range(0, len(arxiv_ids), max_per_request):
            future = executor.submit(
                _get_paper_info_with_sleep, arxiv_ids[i : i + max_per_request], sleep
            )
            future_to_idx[future] = (i, i + max_per_request)
        for future in futures.as_completed(future_to_idx):
            s, e = future_to_idx[future]
            try:
                results.extend(future.result())
            except Exception as exc:
                failed_ids.extend(arxiv_ids[s:e])
                logging.error(exc)
    if failed_ids:
        logging.warn(f"Failed IDs: {failed_ids}")
    return results


def maybe_arxiv_id_to_url(arxiv_id):
    if arxiv_id is None or re.search(_ARXIV_ID_PATTERN, arxiv_id) is None:
        return None
    # TODO: Check arxiv_id is in valid format
    return f"https://arxiv.org/abs/{arxiv_id}"


def maybe_text_to_arxiv_ids(txt):
    optional_version = r"v{0,1}"
    if txt is None:
        return None
    result = re.findall(
        f"arxiv\.org\/(?:abs|pdf)\/({_ARXIV_ID_PATTERN}){optional_version}", txt
    )
    return result


def arxiv_categories_ml_related(arxiv_categories):
    for cat in arxiv_categories:
        if cat[:3].lower() == "cs.":
            return True
    return False
