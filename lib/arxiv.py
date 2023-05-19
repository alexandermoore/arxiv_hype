import arxiv
import pydantic
from typing import List, Optional
import re
from datetime import datetime

_ARXIV_ID_PATTERN = "[0-9]+\.[0-9v]+"

class ArxivPaper(pydantic.BaseModel):
    title: str = ...
    authors: List[str] = ...
    abstract: str = ...
    categories: List[str] = ...
    published: datetime = ...
    updated: Optional[datetime] = None


def get_paper_info(arxiv_ids):
    results = arxiv.Search(id_list=arxiv_ids, max_results=float('inf')).results()
    return [
        ArxivPaper(
            title=r.title,
            authors=[a.name for a in r.authors],
            abstract=r.summary,
            categories=r.categories)
        for r in results]


def maybe_arxiv_id_to_url(arxiv_id):
    if arxiv_id is None or re.search(_ARXIV_ID_PATTERN, arxiv_id) is None:
        return None
    # TODO: Check arxiv_id is in valid format
    return f"https://arxiv.org/abs/{arxiv_id}"

def maybe_arxiv_url_to_id(url):
    if url is None:
        return None
    result = re.findall(f"arxiv\.org\/(?:abs|pdf)\/({_ARXIV_ID_PATTERN})", url)
    print(result)
    return result[0] if result else None