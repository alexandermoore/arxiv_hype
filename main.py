from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from lib import database, embedding, util, twitter
import logging
import asyncio
from typing import List, Annotated
from fastapi.middleware.cors import CORSMiddleware
import pydantic


app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = database.Database()
model = embedding.SentenceTransformer()
# Warm up model
model.embed(["test"])


# TODO: Fix database connection loss issue and remove this.
# @repeat_every(seconds=60 * 3)  # 3 minutes
# def check_db_connection_task():
#     logging.info("Checking database")
#     db._pool.check()


@app.post("/register")
async def register():
    return {"hi": "ok"}


@app.get("/embed_tweets")
async def embed_tweets(
    tweet_ids: Annotated[list[int], Query(..., alias="tweet_ids[]")]
):
    # don't allow more than 50 tweet IDs
    if len(tweet_ids) > 50:
        raise HTTPException(status_code=403, detail="More than 50 tweet IDs")
    print("TWEET IDS", tweet_ids)

    async def get_embedded(tweet_id):
        return twitter.getEmbeddedTweetHtml(tweet_id)

    fns = [get_embedded(t) for t in tweet_ids]
    results = await asyncio.gather(*fns)
    print("results", results, fns)

    return {"data": results}


@app.get("/tweets")
async def get_tweets(arxiv_id: str):
    arxiv_id = arxiv_id[:100]
    tweet_ids = db.get_arxiv_tweet_ids(arxiv_id)
    return {"data": tweet_ids}


@app.get("/search")
async def search(
    query: str,
    top_k: int = 10,
    start_date: str = None,
    end_date: str = None,
    require_social: bool = False,
    lexical_query: str = None,
):
    try:
        if query.strip() == "":
            return {"data": []}
        if lexical_query is not None and lexical_query.strip() == "":
            lexical_query = None

        # Limit query length just in case
        query = query[:200]
        if lexical_query:
            lexical_query = lexical_query[:200]
        start_date = util.maybe_date_str_to_datetime(start_date)
        end_date = util.maybe_date_str_to_datetime(end_date)
        top_k = min(max(1, top_k), 500)
        embedding = model.embed([query])[0]
        results = db.get_similar_papers(
            embedding,
            lexical_query=lexical_query,
            top_k=top_k,
            start_date=start_date,
            end_date=end_date,
            require_social=require_social,
        )
        return {"data": results}
    except Exception as ex:
        logging.error(ex)
        raise HTTPException(status_code=500, detail="Error performing search.")
    return {"query": query, "top_k": top_k}


@app.get("/hello")
async def hello():
    return {"hello": "world"}


# app.mount('/',StaticFiles(directory='frontend/dist', html=True), name='frontend')

# uvicorn main:app --reload
