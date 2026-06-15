"""Renders the knowledge graph as an interactive HTML page and a static PNG."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from pyvis.network import Network

import config


def _color(category):
    return config.CATEGORY_COLORS.get(category, config.DEFAULT_COLOR)


def to_html(G: nx.DiGraph, path=None) -> str:
    """Interactive, zoomable graph you can open in any browser."""
    path = path or os.path.join(config.OUTPUT_DIR, "graph.html")
    net = Network(height="800px", width="100%", directed=True,
                  bgcolor="#ffffff", font_color="#222222", notebook=False,
                  cdn_resources="in_line")
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=120)

    for n, d in G.nodes(data=True):
        cat = d.get("category", "concept")
        deg = G.degree(n)
        net.add_node(n, label=n, color=_color(cat),
                     title=f"{n}  ({cat})  \u2022 connections: {deg}",
                     size=14 + 3 * deg)
    for u, v, d in G.edges(data=True):
        net.add_edge(u, v, title=d.get("relation", ""), label=d.get("relation", ""),
                     font={"size": 9, "color": "#666666"})

    net.set_options('{"edges":{"smooth":{"type":"continuous"},"arrows":{"to":{"enabled":true}}}}')
    net.save_graph(path)
    return path


def to_png(G: nx.DiGraph, path=None) -> str:
    """Static image, handy for slides and reports."""
    path = path or os.path.join(config.OUTPUT_DIR, "graph.png")
    plt.figure(figsize=(16, 11))
    pos = nx.spring_layout(G, seed=42, k=0.9)
    node_colors = [_color(d.get("category", "concept")) for _, d in G.nodes(data=True)]
    node_sizes = [600 + 350 * G.degree(n) for n in G.nodes()]

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.95)
    nx.draw_networkx_edges(G, pos, edge_color="#999999", arrows=True, arrowsize=12,
                           width=1.0, connectionstyle="arc3,rad=0.05")
    nx.draw_networkx_labels(G, pos, font_size=7, font_weight="bold")
    edge_labels = nx.get_edge_attributes(G, "relation")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=5.5,
                                 font_color="#555555")

    # Legend by category.
    from matplotlib.patches import Patch
    present = sorted({d.get("category", "concept") for _, d in G.nodes(data=True)})
    handles = [Patch(color=_color(c), label=c) for c in present]
    plt.legend(handles=handles, loc="upper left", fontsize=8, frameon=True)

    plt.title("Japan Shipbuilding & Green-Tech Knowledge Graph", fontsize=14)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path
