from lib import arxiv, database, embedding

def run():
    t = embedding.SentenceTransformer()
    db = database.Database()
    papers = db.get_papers(ids_only=False, required_null_fields=["embedding"])
    batch_size = 8
    for i in range(0, len(papers), batch_size):
        print(i)
        abstracts = [p.abstract for p in papers[i:i+batch_size]]
        embeddings = iter(t.embed(abstracts))
        for p in papers[i:i+batch_size]:
            p.embedding = next(embeddings)
            #print(p.embedding)
    db.insert_papers(papers)

if __name__ == "__main__":
    run()