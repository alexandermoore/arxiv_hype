from lib import arxiv, database, embedding


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
    num_processed = 0
    i = 0
    while i + batch_size <= len(papers):
        s, e = i, i + batch_size
        print(f"{num_processed} - {num_processed+batch_size-1}")
        if s >= upload_every:
            db.insert_papers(papers[:s], insert_type="embeddings")
            i = 0
            papers = papers[s:]
        if not papers:
            break
        embed_papers(papers[s:e])
        num_processed += batch_size
        i += batch_size

    # while True:
    #     if i >= len(papers):
    #         break
    #     print(num_processed)
    #     abstracts = [p.abstract for p in papers[i : i + batch_size]]
    #     embeddings = iter(t.embed(abstracts))
    #     for p in papers[i : i + batch_size]:
    #         p.embedding = next(embeddings)
    #         # print(p.embedding)
    #     if i + batch_size >= upload_every:
    #         i = 0
    #         db.insert_papers(papers[: i + batch_size], insert_type="embeddings")
    #         if i + batch_size < len(papers):
    #             papers = papers[i + batch_size :]
    #         else:
    #             papers = []
    #     else:
    #         i += batch_size
    #     num_processed += batch_size
    if papers:
        print(f"Final push adding {len(papers)} papers...")
        embed_papers(papers)
        db.insert_papers(papers, insert_type="embeddings")


if __name__ == "__main__":
    run()
