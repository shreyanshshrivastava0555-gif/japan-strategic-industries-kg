"""Builds, saves and loads the knowledge graph from extracted triples."""
import json
import os
from typing import List

import networkx as nx

import config
from extractor import Triple


def build_graph(triples: List[Triple]) -> nx.DiGraph:
    """Create a directed graph; node 'category' comes from the triple types."""
    G = nx.DiGraph()

    def add_node(name, category):
        if name in G:
            # Keep the more specific category if the existing one is generic.
            if G.nodes[name].get("category", "concept") == "concept":
                G.nodes[name]["category"] = category
        else:
            G.add_node(name, category=category)

    for t in triples:
        add_node(t.source, t.source_type)
        add_node(t.target, t.target_type)
        G.add_edge(t.source, t.target, relation=t.relation)
    return G


def merge_triples(G: nx.DiGraph, triples: List[Triple]) -> nx.DiGraph:
    """Add new triples into an existing graph (in place) and return it."""
    def add_node(name, category):
        if name in G:
            if G.nodes[name].get("category", "concept") == "concept":
                G.nodes[name]["category"] = category
        else:
            G.add_node(name, category=category)

    for t in triples:
        add_node(t.source, t.source_type)
        add_node(t.target, t.target_type)
        G.add_edge(t.source, t.target, relation=t.relation)
    return G


def graph_stats(G: nx.DiGraph) -> dict:
    categories = {}
    for _, d in G.nodes(data=True):
        c = d.get("category", "concept")
        categories[c] = categories.get(c, 0) + 1
    degrees = dict(G.degree())
    top_hubs = sorted(degrees.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "by_category": categories,
        "top_hubs": top_hubs,
    }


def save_graph(G: nx.DiGraph, path=None) -> str:
    path = path or os.path.join(config.OUTPUT_DIR, "graph.json")
    data = {
        "nodes": [{"id": n, **d} for n, d in G.nodes(data=True)],
        "edges": [{"source": u, "target": v, **d} for u, v, d in G.edges(data=True)],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_graph(path=None) -> nx.DiGraph:
    path = path or os.path.join(config.OUTPUT_DIR, "graph.json")
    with open(path) as f:
        data = json.load(f)
    G = nx.DiGraph()
    for n in data["nodes"]:
        nid = n.pop("id")
        G.add_node(nid, **n)
    for e in data["edges"]:
        u, v = e.pop("source"), e.pop("target")
        G.add_edge(u, v, **e)
    return G
