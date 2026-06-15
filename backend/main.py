"""
FastAPI backend for the Knowledge Graph Builder Agent.

Designed for concurrency:
* Async endpoints; CPU/IO-bound work is offloaded to a threadpool so the event
  loop is never blocked (lets one worker juggle many simultaneous users).
* Lock-free reads via the copy-on-write GraphService.
* In-memory answer caching for repeated questions.
* A lightweight in-process rate limiter to stay healthy under bursts.

Run (dev):   uvicorn main:app --reload
Run (prod):  gunicorn -c gunicorn_conf.py main:app
"""
import asyncio
import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import schemas
from services import service

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(HERE), "frontend")

app = FastAPI(
    title="Japan Strategic Industries — Knowledge Graph API",
    description="Agentic GenAI knowledge-graph model for Japan's shipbuilding & green-tech study.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Simple sliding-window rate limiter (per client IP).
# --------------------------------------------------------------------------
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MIN", "600"))
_hits = defaultdict(deque)
_rl_lock = asyncio.Lock()


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        async with _rl_lock:
            dq = _hits[ip]
            while dq and now - dq[0] > 60:
                dq.popleft()
            if len(dq) >= RATE_LIMIT:
                return JSONResponse(status_code=429,
                                    content={"detail": "Rate limit exceeded. Slow down a bit."})
            dq.append(now)
    return await call_next(request)


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": service.stats()["version"]}


@app.get("/api/stats")
async def stats():
    return await asyncio.to_thread(service.stats)


@app.get("/api/graph")
async def graph():
    return await asyncio.to_thread(service.graph_data)


@app.get("/api/suggestions")
async def suggestions():
    return {"suggestions": [
        "How does the Imabari–JMU merger connect to Japan's emissions goal?",
        "What are the offshore wind targets?",
        "How is hydrogen related to zero emission ships?",
        "How does shipbuilding converge with green technology?",
        "What is the 7th Basic Energy Plan?",
        "What are Japan's hydrogen targets?",
    ]}


@app.post("/api/ask", response_model=schemas.AskResponse)
async def ask(req: schemas.AskRequest):
    result = await asyncio.to_thread(service.ask, req.question)
    return result


@app.post("/api/build")
async def build():
    return await asyncio.to_thread(service.build_from_brief)


@app.post("/api/fetch")
async def fetch(req: schemas.FetchRequest):
    result = await asyncio.to_thread(
        service.fetch_live, req.query, req.per_query, req.fresh, True
    )
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result.get("error", "Fetch failed"))
    return result


# --------------------------------------------------------------------------
# Frontend (served by the same app for a one-command deploy).
# --------------------------------------------------------------------------
if os.path.isdir(FRONTEND_DIR):
    @app.get("/")
    async def index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
