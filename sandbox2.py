from lib import embedding, database
import time

# t = embedding.SentenceTransformer()
db = database.Database()
# papers = db.get_papers(ids_only=False, required_null_fields=["embedding"])
# batch_size = 8
# for i in range(0, len(papers), batch_size):
#     print(i)
#     abstracts = [p.abstract for p in papers[i:i+batch_size]]
#     embeddings = iter(t.embed(abstracts))
#     for p in papers[i:i+batch_size]:
#         p.embedding = next(embeddings)
#         #print(p.embedding)
# db.insert_papers(papers)

# embedding = t.embed(["Gravitational pull"])[0]
# print("Embedded")
# similar = db.get_similar_papers(embedding=embedding, top_k=5)
# print(similar.title)
db.update_arxiv_social_metrics()
# print(abstract)
# s = time.time()
# print(len(t.embed([abstract])[0].tolist()))
# print(time.time() - s)