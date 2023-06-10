from lib import embedding, database
import time

# t = embedding.SentenceTransformer()
# db = database.Database()
# db.create_tables()
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
# db.update_arxiv_social_metrics()
# print(abstract)
# s = time.time()
# print(len(t.embed([abstract])[0].tolist()))
# print(time.time() - s)

import hmac
import hashlib


def _verify_github_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.
    See: https://docs.github.com/en/webhooks-and-events/webhooks/securing-your-webhooks

    Raise and return 403 if not authorized.

    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    print(payload_body, [secret_token], signature_header)
    if not signature_header:
        raise Exception("x-hub-signature-256 header is missing!")
    hash_object = hmac.new(
        secret_token.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    print("GOT:", signature_header, "EXPECT:", expected_signature)
    if not hmac.compare_digest(expected_signature, signature_header):
        raise Exception("Request signatures didn't match!")


BODY = b"""
{
  "event": "workflow_dispatch",
  "repository": "alexandermoore/arxiv_hype",
  "commit": "f6551e72069f298afe46795315a6ffc69153ed8f",
  "ref": "refs/heads/main",
  "head": null,
  "workflow": "learn-github-actions",
  "requestID": "b8d62e85-24a6-475c-8e45-19bebbc23079"
}
""".strip()

_verify_github_signature(
    BODY,
    secret_token="12345",
    signature_header="sha256=d2c523d7a11fa123ec0debe899be2c78a6438765eca17db39e831f21ed51585a",
)
