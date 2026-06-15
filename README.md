# Japan Strategic Industries — Knowledge Graph Platform

A full-stack **agentic GenAI / LLM** application for the *Japan Shipbuilding &
Green-Technology* study. It reads research documents (and live web news),
extracts entities + relationships into a **knowledge graph**, and lets users
**ask questions in plain English** through a modern web UI — with the answer
path highlighted live on the graph.

Built to serve **hundreds of concurrent users** (load-tested at 300 concurrent
with zero failures — see below).

```
┌─────────────┐     HTTP/JSON      ┌──────────────────────┐
│  Frontend   │ ◄────────────────► │  FastAPI Backend     │
│ (vis-network│                    │  • async endpoints   │
│  SPA)       │                    │  • rate limiting     │
└─────────────┘                    │  • answer caching    │
                                   └──────────┬───────────┘
                                              │
                                   ┌──────────▼───────────┐
                                   │  GraphService        │
                                   │  (copy-on-write,     │
                                   │   thread-safe)       │
                                   └──────────┬───────────┘
                                              │
            ┌─────────────────┬──────────────┼───────────────┐
            ▼                 ▼               ▼               ▼
        extractor.py      fetcher.py      graph.py        query.py
        (LLM / offline)  (live web news) (NetworkX)     (GraphRAG)
```

## Project layout

| Folder | What it is |
|--------|------------|
| `knowledge_graph/` | The core model (extraction, graph, query, live fetch) + CLI |
| `backend/`         | FastAPI server, concurrency layer, load test, run scripts |
| `frontend/`        | Modern single-page web app (graph + chat + dashboard) |
| `docs/`            | The Idea-F explainer PDF |

## Quick start

```bash
# 1. Create the environment
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 2. Run the whole app (frontend + API) on one port
cd backend
./run.sh 8000           # production: multiple workers
# or for development:
./run_dev.sh 8000       # single worker, auto-reload

# 3. Open the UI
open http://localhost:8000
```

The first launch auto-builds the graph from `knowledge_graph/data/japan_brief.txt`.

### Optional: use a real LLM
By default it runs an **offline extractor** (no key needed). To switch to a live
LLM for extraction and answers:

```bash
export OPENAI_API_KEY="sk-..."
```

## Features

- **Interactive knowledge graph** — zoom, drag, search, click nodes.
- **Ask the graph** — natural-language Q&A; the answer path lights up on the graph.
- **Live data** — one click pulls the latest real news from the web and merges it in.
- **Insights dashboard** — category breakdown, most-connected hubs, live stats.
- **Runs with no API key** — offline mode works out of the box; add a key for full LLM.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health`      | Liveness check |
| GET  | `/api/stats`       | Graph statistics (memoized) |
| GET  | `/api/graph`       | Nodes + edges for the visualization (memoized) |
| GET  | `/api/suggestions` | Sample questions |
| POST | `/api/ask`         | `{question}` → answer + entities + paths |
| POST | `/api/build`       | Rebuild the graph from the brief |
| POST | `/api/fetch`       | Pull live news and merge into the graph |

Interactive API docs at `http://localhost:8000/docs`.

## How it scales to hundreds of users

1. **Async FastAPI** — every endpoint is async; blocking work (graph walking,
   serialization, fetching) is offloaded to a threadpool so the event loop
   never stalls.
2. **Copy-on-write graph** — reads (the hot path) are **lock-free**. Writes build
   a new graph and atomically swap the reference; a lock only serializes writers.
3. **Per-version memoization** — `/graph` and `/stats` payloads are computed once
   per graph version, not per request.
4. **Answer cache** — identical questions are served from an in-memory LRU+TTL
   cache (keyed by graph version), so popular questions cost ~0.
5. **Multi-worker deployment** — Gunicorn runs several Uvicorn workers across all
   CPU cores.
6. **Rate limiting** — a per-IP sliding window protects the service from bursts.

### Load-test results (this machine, 8 cores, 6 workers)

300 concurrent connections, 30,000 requests each, keep-alive:

| Endpoint | Throughput | p50 | p95 | p99 | Failures |
|----------|-----------:|----:|----:|----:|---------:|
| `GET /api/graph` | 4,463 req/s | 57 ms | 134 ms | 197 ms | 0 / 30,000 |
| `POST /api/ask`  | 6,943 req/s | 29 ms | 89 ms  | 238 ms | 0 / 30,000 |

Reproduce:

```bash
cd backend
# Python async client:
python load_test.py http://localhost:8000 200 5
# Or ApacheBench (use 127.0.0.1 on macOS, -k for keep-alive):
ab -k -n 30000 -c 300 -l http://127.0.0.1:8000/api/graph
```

## CLI (no server needed)

```bash
cd knowledge_graph
python app.py build           # build graph from the brief
python app.py fetch           # pull live web news
python app.py ask "How does Imabari connect to Japan's emissions goal?"
python app.py chat            # interactive Q&A
python app.py stats           # graph statistics
```

## License

Released under the [MIT License](LICENSE).
