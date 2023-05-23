from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from lib import database, embedding, util
import logging
from fastapi.middleware.cors import CORSMiddleware

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


@app.post("/register")
async def register():
    return {"hi": "ok"}


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
