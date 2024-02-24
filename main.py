from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from lib import database, embedding, util, twitter
from pipeline import run_pipeline
import logging
import asyncio
import threading
from typing import List, Annotated
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import hashlib
import hmac
import random
import time
import os
import requests

# from fastapi.utils import tasks

# To run this in dev:
# uvicorn main:fastapi_app --reload

logging.getLogger().setLevel(logging.INFO)

fastapi_app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173",
]

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = database.Database()

# Event loop
# try:
#     EVENT_LOOP = asyncio.get_running_loop()
# except RuntimeError:
#     EVENT_LOOP = asyncio.new_event_loop()
#     asyncio.set_event_loop(EVENT_LOOP)

_MODEL = None


# class ModelHandler:
#     def __init__(self):
#         # OLD WAY
#         # self._is_loaded_event = asyncio.Event()
#         # self._model = None
#         # EVENT_LOOP.run_in_executor(None, self.load)
#         self._is_loaded_event = asyncio.Event()
#         self._model = None
#         self.load()

#     async def load(self):
#         model = embedding.SentenceTransformer()
#         model.embed(["t"])
#         logging.info("Model loading complete.")
#         self._model = model
#         self._is_loaded_event.set()

#     async def get_embedding_model(self):
#         await self._is_loaded_event.wait()
#         return self._model


class ModelHandlerV2:
    def __init__(self):
        logging.info("Starting model loading")
        model = embedding.SentenceTransformer()
        model.embed(["t"])
        logging.info("Model loading complete.")
        self._model = model

    def get_embedding_model(self):
        return self._model


_model_handler = None


def load_model_handler():
    global _model_handler
    _model_handler = ModelHandlerV2()


load_thread = threading.Thread(target=load_model_handler)
load_thread.start()


def model_handler() -> ModelHandlerV2:
    while _model_handler is None:
        continue
    return _model_handler


# async def get_embedding_model():
#     global _MODEL
#     if _MODEL is None:
#         _MODEL = embedding.SentenceTransformer()
#         _MODEL.embed(["t"])
#     return _MODEL


# model = embedding.SentenceTransformer()
# # Warm up model (double check if need to do this)
# model.embed(["t"])


# TODO: Fix database connection loss issue and remove this.
# @tasks.repeat_every(seconds=60 * 2)  # 2 minutes
# async def check_db_connection_task():
#     logging.info("Checking database connections.")
#     db._pool.check()


def _verify_github_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.
    See: https://docs.github.com/en/webhooks-and-events/webhooks/securing-your-webhooks

    Raise and return 403 if not authorized.

    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    if not signature_header:
        raise HTTPException(
            status_code=403, detail="x-hub-signature-256 header is missing!"
        )
    hash_object = hmac.new(
        secret_token.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=403, detail="Request signatures didn't match!")


@fastapi_app.get("/embed_tweets")
async def embed_tweets(
    # to handle format of tweet_ids[]= rather than tweet_ids=
    tweet_ids: Annotated[list[int], Query(..., alias="tweet_ids[]")]
):
    # don't allow more than 50 tweet IDs
    if len(tweet_ids) > 50:
        raise HTTPException(status_code=403, detail="More than 50 tweet IDs")

    async def get_embedded(tweet_id):
        return twitter.getEmbeddedTweetHtml(tweet_id)

    fns = [get_embedded(t) for t in tweet_ids]
    results = await asyncio.gather(*fns)

    return {"data": results}


@fastapi_app.get("/tweets")
async def get_tweets(arxiv_id: str):
    arxiv_id = arxiv_id[:100]
    tweet_ids = db.get_arxiv_tweet_ids(arxiv_id)
    return {"data": tweet_ids}


@fastapi_app.get("/hnews")
async def get_tweets(arxiv_id: str):
    arxiv_id = arxiv_id[:100]
    hnews_ids = db.get_arxiv_hnews_ids(arxiv_id)
    return {"data": hnews_ids}


@fastapi_app.get("/search")
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
        model = model_handler().get_embedding_model()
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
        raise ex
        # raise HTTPException(status_code=500, detail="Error performing search.")
    # return {"query": query, "top_k": top_k}


def _run_pipeline(start_dt=None, embedding_model=None):
    logging.info(
        f"Running pipeline with start_dt={start_dt}, embedding_model={embedding_model}"
    )
    run_pipeline.run(start_dt=start_dt, embedding_model=embedding_model)


def _keep_server_alive(duration, base_url):
    """fly.io shuts down after a period of inactivity.
    Use this to keep the server on for a duration.
    """
    # Super hacky way to tell if it's in prod
    if "localhost" in base_url:
        return

    ping_url = os.path.join(os.path.dirname(base_url), "ping")

    stime = time.time()
    while time.time() - stime < duration:
        ctime = time.time() - stime
        logging.info(f"Pinging to keep server alive... ({int(ctime)}/{duration})")
        _ = requests.get(ping_url)
        time.sleep(20 + int(random.random() * 10))


@fastapi_app.post("/gh_webhook_update_db")
async def gh_webhook_update_db(request: Request):
    logging.info("STARTING GH WEBHOOK UPDATE")
    # Verify request
    _verify_github_signature(
        payload_body=await request.body(),
        secret_token=util.get_env_var("GITHUB_WEBHOOK_SECRET", must_exist=True),
        signature_header=request.headers.get("x-hub-signature-256"),
    )
    logging.info("VERIFIED GH WEBHOOK UPDATE")

    start_dt = datetime.today() - timedelta(days=365)

    # Start a separate task for updating event
    # loop = asyncio.get_running_loop()
    # with concurrent.futures.ProcessPoolExecutor() as pool:
    # EVENT_LOOP.run_in_executor(
    #     None, _run_pipeline, start_dt, await model_handler.get_embedding_model()
    # )

    # loop = asyncio.get_running_loop()
    # loop.create_task(_run_pipeline(start_dt=start_dt, embedding_model=model))

    # Keep server alive for 15min
    # EVENT_LOOP.run_in_executor(None, _keep_server_alive, 15 * 60, str(request.url))

    def _run_pipeline_wrapper_fn():
        _run_pipeline(
            start_dt=start_dt, embedding_model=model_handler().get_embedding_model()
        )

    threading.Thread(target=_run_pipeline_wrapper_fn).start()
    # threading.Thread(
    #     target=_run_pipeline,
    #     kwargs={
    #         "start_dt": start_dt,
    #         "embedding_model": model_handler().get_embedding_model(),
    #     },
    # ).start()
    threading.Thread(
        target=_keep_server_alive,
        kwargs={"duration": 15 * 60, "base_url": str(request.url)},
    ).start()
    logging.info("RETURNING FROM GH WEBHOOK UPDATE")


# @fastapi_app.get("/hello")
# async def hello(request: Request):
#     return {"hello": "world"}


@fastapi_app.get("/ping")
async def ping(request: Request):
    return {"ping": random.random()}


fastapi_app.mount(
    "/", StaticFiles(directory="frontend/dist", html=True), name="frontend"
)

# uvicorn main:app --reload
