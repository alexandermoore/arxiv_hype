from lib import arxiv, database
import logging


def run():
    db = database.Database()
    arxiv_ids = db.get_papers(ids_only=True, required_null_fields=("title",))
    logging.info(f"Updating {len(arxiv_ids)} papers")
    results = arxiv.get_paper_info_parallel(
        arxiv_ids, max_per_request=100, max_workers=1, sleep=3
    )
    logging.info("Updating DB")
    db.insert_papers(results)


if __name__ == "__main__":
    run()
