"""
Generates a PDF that explains Idea F: the Knowledge Graph Builder Agent
for the Japan Shipbuilding & Green-Tech study.

Run:  python make_pdf.py
Output:  docs/Idea_F_Knowledge_Graph.pdf
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, ListFlowable, ListItem,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
os.makedirs(DOCS, exist_ok=True)
DIAGRAM = os.path.join(DOCS, "_sample_graph.png")
PDF_PATH = os.path.join(DOCS, "Idea_F_Knowledge_Graph.pdf")


def build_sample_diagram():
    """Draw a small illustrative knowledge graph for the document."""
    G = nx.DiGraph()
    edges = [
        ("Imabari", "JMU", "acquires 60%"),
        ("Imabari", "Zero-Emission Ships", "builds"),
        ("Zero-Emission Ships", "Hydrogen / Ammonia", "use"),
        ("Hydrogen / Ammonia", "7th Energy Plan", "supported by"),
        ("7th Energy Plan", "46% Emissions Cut", "aims for"),
        ("Shipbuilding Roadmap", "18M GT / 20% Share", "targets"),
        ("Shipbuilding Roadmap", "Imabari", "drives"),
        ("Offshore Wind", "7th Energy Plan", "part of"),
    ]
    for a, b, label in edges:
        G.add_edge(a, b, label=label)

    color_map = {
        "Imabari": "#4C72B0", "JMU": "#4C72B0", "Shipbuilding Roadmap": "#4C72B0",
        "Zero-Emission Ships": "#55A868", "Hydrogen / Ammonia": "#55A868",
        "Offshore Wind": "#55A868",
        "7th Energy Plan": "#C44E52",
        "46% Emissions Cut": "#8172B3", "18M GT / 20% Share": "#8172B3",
    }
    node_colors = [color_map.get(n, "#999999") for n in G.nodes()]

    plt.figure(figsize=(9, 6))
    pos = nx.spring_layout(G, seed=7, k=1.1)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2600, alpha=0.95)
    nx.draw_networkx_labels(G, pos, font_size=8, font_color="white", font_weight="bold")
    nx.draw_networkx_edges(G, pos, edge_color="#666666", arrows=True,
                           arrowsize=16, width=1.4, connectionstyle="arc3,rad=0.06")
    edge_labels = nx.get_edge_attributes(G, "label")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6.5,
                                 font_color="#333333")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(DIAGRAM, dpi=160, bbox_inches="tight")
    plt.close()


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="TitleBig", parent=s["Title"], fontSize=24,
                         textColor=colors.HexColor("#1a3c6e"), spaceAfter=6))
    s.add(ParagraphStyle(name="Subtitle", parent=s["Normal"], fontSize=12,
                         textColor=colors.HexColor("#555555"), spaceAfter=18))
    s.add(ParagraphStyle(name="H2", parent=s["Heading2"], fontSize=15,
                         textColor=colors.HexColor("#1a3c6e"), spaceBefore=14, spaceAfter=6))
    s.add(ParagraphStyle(name="Body", parent=s["Normal"], fontSize=10.5,
                         leading=15, spaceAfter=8))
    s.add(ParagraphStyle(name="Cap", parent=s["Normal"], fontSize=8.5,
                         textColor=colors.HexColor("#777777"), alignment=1, spaceAfter=12))
    return s


def bullets(items, s):
    return ListFlowable(
        [ListItem(Paragraph(t, s["Body"]), leftIndent=10) for t in items],
        bulletType="bullet", start="circle", leftIndent=12,
    )


def build_pdf():
    build_sample_diagram()
    s = styles()
    doc = SimpleDocTemplate(PDF_PATH, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm)
    e = []

    e.append(Paragraph("Idea F: The Knowledge Graph Builder Agent", s["TitleBig"]))
    e.append(Paragraph("An Agentic GenAI / LLM model for Japan's Shipbuilding &amp; Green-Technology Study",
                       s["Subtitle"]))

    e.append(Paragraph("1. The Idea in Simple Words", s["H2"]))
    e.append(Paragraph(
        "Imagine you have a big messy pile of reports about Japan's shipbuilding and green-energy "
        "plans. This AI reads them all and turns them into a simple <b>map of dots and lines</b> &mdash; "
        "and then you can <b>chat with that map</b>. It is like turning many pages of dense reports into "
        "a living mind-map you can talk to.", s["Body"]))

    e.append(Paragraph("2. How It Works", s["H2"]))
    e.append(Paragraph(
        "A knowledge graph has only two things: <b>nodes</b> (the dots = real things like companies, "
        "technologies, policies, targets) and <b>edges</b> (the lines = how they relate, e.g. "
        "\"acquires\", \"funds\", \"targets\", \"threatens\"). The agent reads the documents, pulls out "
        "these dots and lines automatically, stores them, and then answers your questions by walking "
        "along the connections.", s["Body"]))
    e.append(bullets([
        "<b>Read</b> &mdash; the agent ingests reports / PDFs (OECD, METI, Ember, Nippon.com).",
        "<b>Extract</b> &mdash; the LLM pulls out entities (\"Imabari\", \"10 GW\", \"offshore wind\").",
        "<b>Link</b> &mdash; the LLM figures out relationships (\"acquires\", \"targets\", \"supports\").",
        "<b>Build</b> &mdash; it stores everything in a graph database.",
        "<b>Ask</b> &mdash; you ask plain-English questions; the agent answers using the map.",
    ], s))

    e.append(Paragraph("3. Sample Knowledge Graph (from your brief)", s["H2"]))
    e.append(Image(DIAGRAM, width=16*cm, height=10.6*cm))
    e.append(Paragraph(
        "Figure 1: How shipbuilding (blue), green tech (green), policy (red) and national targets "
        "(purple) connect &mdash; visually proving the convergence thesis.", s["Cap"]))

    e.append(Paragraph("4. Why This Is Agentic AI + GenAI + LLM", s["H2"]))
    data = [
        ["Buzzword", "What it actually means in this project"],
        ["Agentic AI", "The AI decides what to extract, merges duplicates, resolves conflicting "
                        "numbers, and walks multi-step paths to answer questions \u2014 it acts, not just chats."],
        ["GenAI / LLM", "The LLM reads messy text, extracts structured entities & relationships, "
                        "and writes human-readable answers from the graph."],
    ]
    t = Table(data, colWidths=[3.2*cm, 12.3*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3c6e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5fa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    e.append(t)
    e.append(Spacer(1, 10))

    e.append(Paragraph("5. Example: Multi-hop Question", s["H2"]))
    e.append(Paragraph(
        "<b>You ask:</b> \"How does the Imabari&ndash;JMU merger connect to Japan's emissions goal?\"",
        s["Body"]))
    e.append(Paragraph(
        "<b>The agent walks the path:</b> Imabari &rarr; acquires JMU &rarr; builds zero-emission ships "
        "&rarr; use hydrogen/ammonia &rarr; supports the 7th Energy Plan &rarr; 46% emissions cut.",
        s["Body"]))
    e.append(Paragraph(
        "<b>It answers:</b> \"Indirectly but strongly &mdash; consolidation gives Japan the scale to "
        "mass-produce ammonia/hydrogen ships, which feed directly into the national decarbonization "
        "target.\"", s["Body"]))

    e.append(Paragraph("6. Technology Stack", s["H2"]))
    e.append(bullets([
        "<b>Graph database:</b> Neo4j (production) or NetworkX (prototype).",
        "<b>Brain:</b> an LLM (GPT / Claude, or self-hosted Llama / Mistral).",
        "<b>Extraction:</b> LLM with structured JSON output.",
        "<b>Query layer (GraphRAG):</b> English question &rarr; graph lookup &rarr; written answer.",
        "<b>Visualization:</b> PyVis / D3.js / Neo4j Bloom.",
    ], s))

    e.append(Paragraph("7. Minimum Viable Product", s["H2"]))
    e.append(bullets([
        "Take the research brief as input text.",
        "LLM extracts entities + relationships into JSON.",
        "Load into NetworkX (no database setup needed).",
        "Draw the graph and answer 2&ndash;3 questions about it.",
    ], s))
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "<i>This MVP is exactly what the accompanying Python model implements.</i>", s["Body"]))

    doc.build(e)
    if os.path.exists(DIAGRAM):
        os.remove(DIAGRAM)
    print(f"PDF written to: {PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
