from lib import database, embedding


def run(embedding_model=None):
    def embed_papers(papers):
        abstracts = [p.abstract for p in papers]
        embeddings = iter(t.embed(abstracts))
        for p in papers:
            p.embedding = next(embeddings)

    if embedding_model is None:
        t = embedding.SentenceTransformer()
    else:
        t = embedding_model
    db = database.Database()
    papers = db.get_papers(ids_only=False, required_null_fields=["embedding"])
    papers = [r.paper for r in papers]
    print(f"Found {len(papers)} missing embeddings.")
    batch_size = 8
    upload_every = batch_size * 10

    embedded_papers = []
    num_processed = 0
    total = len(papers)
    while len(papers):
        batch = papers[:batch_size]
        num_processed += len(batch)
        papers = papers[batch_size:]
        embed_papers(batch)
        embedded_papers.extend(batch)
        if len(embedded_papers) >= upload_every:
            db.insert_papers(embedded_papers, insert_type="embeddings")
            embedded_papers = []
        print(f"Processed {num_processed}/{total}")
    db.insert_papers(embedded_papers, insert_type="embeddings")
    print("Done updating embeddings.")


if __name__ == "__main__":
    run()
