# Knowledge Graph Builder Agent (Idea F)

An **agentic GenAI / LLM** model for the *Japan Shipbuilding & Green-Technology* study.

It reads research documents, uses an LLM to extract **entities** (companies, technologies,
policies, targets) and the **relationships** between them, builds a connected **knowledge
graph**, and lets you **ask the graph questions in plain English**.

> In one line: it turns messy reports into a connect-the-dots map you can talk to.

## What it does

```
READ / FETCH  ->  EXTRACT (LLM)  ->  BUILD graph  ->  VISUALIZE  ->  ASK questions (GraphRAG)
```

It can read a static document **or pull live news from the web** (free, no API key)
and merge the latest events into the graph.

- **Agentic AI**: decides what to extract, merges duplicates, walks multi-step paths to answer.
- **GenAI / LLM**: reads text, outputs structured triples, and writes human-readable answers.
- **Runs without an API key**: ships with an offline extractor (a curated seed graph from the
  brief) so you can demo immediately. Add a key to switch to the live LLM.

## Install

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Use

```bash
# 1. Build the graph (offline by default)
python app.py build

# Optional: use the live LLM for extraction + answers
export OPENAI_API_KEY="sk-..."
python app.py build

# Build from your own document
python app.py build --input path/to/document.txt

# 1b. Pull LIVE data from the web and merge it into the graph
python app.py fetch                                   # default study topics
python app.py fetch --query "Japan offshore wind 2030"   # custom search
python app.py fetch --fresh                            # build from live data only

# 2. Ask questions
python app.py ask "How does the Imabari-JMU merger connect to Japan's emissions goal?"

# 3. Interactive chat
python app.py chat

# 4. Inspect the graph
python app.py stats
```

## Outputs (in `output/`)

| File         | What it is                               |
|--------------|------------------------------------------|
| `graph.json` | The knowledge graph (nodes + edges)      |
| `graph.html` | Interactive, zoomable graph (open in a browser) |
| `graph.png`  | Static image for slides / reports        |

## Files

| File            | Role                                            |
|-----------------|-------------------------------------------------|
| `extractor.py`  | LLM + offline triple extraction + news mining   |
| `fetcher.py`    | Live web/news fetching (Google News RSS + article scraping) |
| `graph.py`      | Build / save / load / merge the NetworkX graph  |
| `visualize.py`  | Interactive HTML + static PNG rendering         |
| `query.py`      | GraphRAG query agent (finds entities, walks paths) |
| `app.py`        | Command-line interface                          |
| `config.py`     | Settings, colors, API key                       |
| `data/japan_brief.txt` | The study brief used as input            |

## How to extend

- Drop more documents into `data/` and run `build --input` on each (graphs merge if you
  extend `app.py` to append).
- Swap NetworkX for **Neo4j** for a production database.
- Replace the offline seed with the live LLM for any new domain — the pipeline is generic.
