"""
GraphService: a thread-safe, in-memory service around the knowledge graph,
designed to serve hundreds of concurrent users.

Concurrency strategy
--------------------
* Reads (ask / graph / stats) are the hot path. They are LOCK-FREE: every read
  grabs the current graph reference; queries never mutate it.
* Writes (build / fetch) build a brand-new graph off to the side and then
  ATOMICALLY swap the reference (copy-on-write). A small lock only serializes
  writers against each other, never against readers.
* A bumping `version` invalidates the answer cache whenever the graph changes.
* Query answers are cached (keyed by version + question) so repeated/identical
  questions from many users are served instantly.
"""
import os
import sys
import threading
import time
from collections import OrderedDict
from typing import Optional

# Make the knowledge_graph package importable.
KG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_graph")
if KG_DIR not in sys.path:
    sys.path.insert(0, KG_DIR)

import networkx as nx  # noqa: E402

import config as kg_config          # noqa: E402
import extractor as extractor_mod   # noqa: E402
import graph as graph_mod           # noqa: E402
import fetcher as fetcher_mod       # noqa: E402
from query import GraphQueryAgent   # noqa: E402

GRAPH_PATH = os.path.join(kg_config.OUTPUT_DIR, "graph.json")
BRIEF_PATH = os.path.join(kg_config.DATA_DIR, "japan_brief.txt")


class _TTLCache:
    """Tiny thread-safe LRU + TTL cache for query answers."""

    def __init__(self, maxsize=512, ttl=600):
        self.maxsize = maxsize
        self.ttl = ttl
        self._data = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            value, ts = item
            if time.time() - ts > self.ttl:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key, value):
        with self._lock:
            self._data[key] = (value, time.time())
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def clear(self):
        with self._lock:
            self._data.clear()


class GraphService:
    def __init__(self):
        self._graph: nx.DiGraph = nx.DiGraph()
        self._agent: Optional[GraphQueryAgent] = None
        self._version = 0
        self._write_lock = threading.Lock()   # writers only
        self._cache = _TTLCache()
        self._last_updated = None
        self._extractor_mode = "offline"
        # Memoized derived data, recomputed only when the version changes.
        self._derived_version = -1
        self._derived_stats = None
        self._derived_graph_data = None
        self._derived_lock = threading.Lock()
        self._load_or_build()

    # ---- lifecycle -------------------------------------------------------
    def _load_or_build(self):
        if os.path.exists(GRAPH_PATH):
            try:
                G = graph_mod.load_graph(GRAPH_PATH)
                self._swap(G)
                return
            except Exception:
                pass
        self.build_from_brief()

    def _swap(self, new_graph: nx.DiGraph):
        """Atomically replace the live graph and refresh derived state."""
        self._graph = new_graph
        self._agent = GraphQueryAgent(new_graph)
        self._version += 1
        self._last_updated = time.time()
        self._cache.clear()

    # ---- reads (lock-free hot path) -------------------------------------
    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    def _ensure_derived(self):
        """Compute stats + graph_data once per version (cheap thereafter)."""
        if self._derived_version == self._version:
            return
        with self._derived_lock:
            if self._derived_version == self._version:
                return
            G = self._graph
            s = graph_mod.graph_stats(G)
            s["version"] = self._version
            s["last_updated"] = self._last_updated
            s["extractor_mode"] = self._extractor_mode

            nodes = []
            for n, d in G.nodes(data=True):
                cat = d.get("category", "concept")
                nodes.append({
                    "id": n, "label": n, "group": cat,
                    "color": kg_config.CATEGORY_COLORS.get(cat, kg_config.DEFAULT_COLOR),
                    "value": 1 + G.degree(n),
                })
            edges = [{"from": u, "to": v, "label": d.get("relation", "")}
                     for u, v, d in G.edges(data=True)]

            self._derived_stats = s
            self._derived_graph_data = {"nodes": nodes, "edges": edges, "version": self._version}
            self._derived_version = self._version

    def stats(self) -> dict:
        self._ensure_derived()
        return self._derived_stats

    def graph_data(self) -> dict:
        """Nodes + edges in a frontend-friendly (vis-network) shape (memoized)."""
        self._ensure_derived()
        return self._derived_graph_data

    def ask(self, question: str) -> dict:
        question = (question or "").strip()
        if not question:
            return {"question": "", "answer": "Please enter a question.",
                    "entities": [], "paths": [], "facts": [], "mode": "offline"}
        key = (self._version, question.lower())
        cached = self._cache.get(key)
        if cached is not None:
            return {**cached, "cached": True}
        result = self._agent.answer_structured(question)
        self._cache.set(key, result)
        return {**result, "cached": False}

    # ---- writes (serialized, copy-on-write) -----------------------------
    def build_from_brief(self, offline: bool = None) -> dict:
        with self._write_lock:
            with open(BRIEF_PATH) as f:
                text = f.read()
            force_offline = True if offline is None else offline
            ext, mode = extractor_mod.get_extractor(force_offline=force_offline)
            self._extractor_mode = mode
            triples = ext.extract(text)
            G = graph_mod.build_graph(triples)
            graph_mod.save_graph(G, GRAPH_PATH)
            self._swap(G)
            return {"ok": True, "mode": mode, "triples": len(triples), **self.stats()}

    def fetch_live(self, query: str = None, per_query: int = 6,
                   fresh: bool = False, offline: bool = True) -> dict:
        with self._write_lock:
            queries = [query] if query else kg_config.LIVE_QUERIES
            items = fetcher_mod.fetch_all_news(queries, per_query=per_query)
            if not items:
                return {"ok": False, "error": "No news items returned.", **self.stats()}

            ext, mode = extractor_mod.get_extractor(force_offline=offline)
            if mode == "llm":
                triples = ext.extract(fetcher_mod.news_to_text(items))
            else:
                triples = extractor_mod.mine_news_triples(items)

            if fresh:
                G = graph_mod.build_graph(triples)
            else:
                # Start from a copy of the live graph so readers are unaffected
                # until we swap.
                G = self._graph.copy()
                graph_mod.merge_triples(G, triples)

            graph_mod.save_graph(G, GRAPH_PATH)
            self._swap(G)
            headlines = [{"title": it["title"], "source": it.get("source", ""),
                          "link": it.get("link", "")} for it in items[:12]]
            return {"ok": True, "mode": mode, "items": len(items),
                    "triples": len(triples), "headlines": headlines, **self.stats()}


# Process-wide singleton.
service = GraphService()
