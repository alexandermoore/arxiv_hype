from lib import arxiv, database

def run():
    db = database.Database()
    arxiv_ids = db.get_all_arxiv_ids(incomplete_only=False)
    print(f"Updating {len(arxiv_ids)} papers")
    results = arxiv.get_paper_info_parallel(
        arxiv_ids,
        max_per_request=100,
        max_workers=1,
        sleep=3)
    print("Updating DB")
    db.insert_papers(results)

if __name__ == "__main__":
    run()