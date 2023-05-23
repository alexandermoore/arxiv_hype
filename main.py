from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from lib import database, embedding
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


@app.post('/register')
async def register():
    return {"hi": "ok"}


@app.get('/search')
async def search(query: str, top_k: int = 10):
    try:
        embedding = model.embed([query])[0]
        results = db.get_similar_papers(embedding, top_k=top_k)
        return results
    except Exception as ex:
        logging.error(ex)
        raise HTTPException(status_code=500, detail="Internal server error.")
    return {"query": query, "top_k": top_k}


@app.get('/hello')
async def hello():
    return {"hello": "world"}
 
#app.mount('/',StaticFiles(directory='frontend/dist', html=True), name='frontend')

# uvicorn main:app --reload