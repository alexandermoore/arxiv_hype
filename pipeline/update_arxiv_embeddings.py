from lib import arxiv, database, embedding


def run():
    t = embedding.SentenceTransformer()
    db = database.Database()
    papers = db.get_papers(ids_only=False, required_null_fields=["embedding"])
    papers = [r.paper for r in papers]
    print(f"Found {len(papers)} missing embeddings.")
    batch_size = 8
    upload_every = batch_size * 10
    num_processed = 0
    i = 0
    while True:
        if i >= len(papers):
            break
        print(num_processed)
        abstracts = [p.abstract for p in papers[i : i + batch_size]]
        embeddings = iter(t.embed(abstracts))
        for p in papers[i : i + batch_size]:
            p.embedding = next(embeddings)
            # print(p.embedding)
        if i + batch_size >= upload_every:
            db.insert_papers(papers[: i + batch_size], insert_type="embeddings")
            if i + batch_size < len(papers):
                papers = papers[i + batch_size :]
            else:
                papers = []
        else:
            i += batch_size
        num_processed += batch_size
    if papers:
        db.insert_papers(papers, insert_type="embeddings")


if __name__ == "__main__":
    run()
