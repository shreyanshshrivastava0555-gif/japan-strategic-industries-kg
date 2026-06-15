"""
Query layer (GraphRAG-style).

Given a natural-language question, the agent:
  1. Finds the entities in the question that match graph nodes.
  2. Walks the graph (paths / neighborhoods) to gather relevant facts.
  3. Turns those facts into a written answer (LLM if available, else a clear
     template-based explanation built from the graph paths).
"""
import difflib
import re
from typing import List, Optional

import networkx as nx

import config


STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "and", "how", "what", "does",
    "do", "in", "on", "for", "with", "by", "connect", "connected", "related",
    "relate", "between", "japan", "japans", "goal", "goals", "target", "plan",
    "why", "where", "which", "that", "this", "it", "its", "about", "tell", "me",
}


def _tokens(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9%\-]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def find_entities(G: nx.DiGraph, question: str, limit: int = 6,
                  node_tokens: dict = None) -> List[str]:
    """Match question words to node names via substring + fuzzy matching.

    `node_tokens` (name -> (lowername, token_set)) can be precomputed once per
    graph version to keep this fast under load.
    """
    q = question.lower()
    qtoks = set(_tokens(question))
    if node_tokens is None:
        node_tokens = {n: (n.lower(), set(_tokens(n))) for n in G.nodes()}

    scored = []
    for n, (nl, ntoks) in node_tokens.items():
        score = 0.0
        if nl in q:
            score = 1.0
        elif ntoks:
            overlap = len(ntoks & qtoks) / len(ntoks)
            score = overlap
            if score < 0.7:  # only pay for fuzzy matching when needed
                for qt in qtoks:
                    best = max((difflib.SequenceMatcher(None, qt, nt).ratio()
                                for nt in ntoks), default=0)
                    if best > 0.85:
                        score = max(score, 0.7)
                        break
        if score > 0.35:
            scored.append((score, n))
    scored.sort(reverse=True)
    return [n for _, n in scored[:limit]]


def _undirected_path(G: nx.DiGraph, a: str, b: str, UG=None) -> Optional[List[str]]:
    UG = UG if UG is not None else G.to_undirected(as_view=True)
    try:
        return nx.shortest_path(UG, a, b)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def _describe_edge(G: nx.DiGraph, u: str, v: str) -> str:
    if G.has_edge(u, v):
        return f"{u} --{G[u][v].get('relation','related to')}--> {v}"
    if G.has_edge(v, u):
        return f"{v} --{G[v][u].get('relation','related to')}--> {u}"
    return f"{u} -- {v}"


def gather_facts(G: nx.DiGraph, entities: List[str], UG=None) -> dict:
    """Collect paths between entity pairs + immediate neighborhoods."""
    facts = {"paths": [], "neighbors": {}}
    if UG is None:
        UG = G.to_undirected(as_view=True)

    seen_paths = set()
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            path = _undirected_path(G, entities[i], entities[j], UG=UG)
            if path and len(path) > 1:
                sig = tuple(path)
                if sig in seen_paths:
                    continue
                seen_paths.add(sig)
                steps = [_describe_edge(G, path[k], path[k + 1])
                         for k in range(len(path) - 1)]
                facts["paths"].append({"path": path, "steps": steps})

    # Show the most informative connections first (longer chains tell a story).
    facts["paths"].sort(key=lambda p: len(p["steps"]), reverse=True)

    for e in entities:
        nb = []
        for succ in G.successors(e):
            nb.append(f"{e} --{G[e][succ].get('relation','')}--> {succ}")
        for pred in G.predecessors(e):
            nb.append(f"{pred} --{G[pred][e].get('relation','')}--> {e}")
        facts["neighbors"][e] = nb[:12]
    return facts


def _template_answer(question: str, entities: List[str], facts: dict) -> str:
    if not entities:
        return ("I couldn't match anything in your question to the graph. "
                "Try names like 'Imabari', 'hydrogen', 'offshore wind', "
                "'7th Energy Plan', or 'emissions'.")

    lines = [f"Question: {question}", ""]
    lines.append("Matched entities: " + ", ".join(entities))
    lines.append("")

    if facts["paths"]:
        lines.append("Connections found by walking the graph:")
        for p in facts["paths"][:5]:
            lines.append("  " + "  ".join(p["steps"]))
        lines.append("")
        # Build a plain-language story from the richest path's step strings,
        # which look like "Source --relation--> Target".
        story_bits = []
        for step in facts["paths"][0]["steps"]:
            story_bits.append(step.replace(" --", " ").replace("--> ", " "))
        lines.append("In plain words: " + "; ".join(story_bits) + ".")
    else:
        lines.append("Direct facts about the matched entities:")
        for e, nb in facts["neighbors"].items():
            for f in nb:
                lines.append("  " + f)
    return "\n".join(lines)


class GraphQueryAgent:
    def __init__(self, G: nx.DiGraph):
        self.G = G
        # Precompute reusable structures once (per graph version) for speed.
        self.UG = G.to_undirected(as_view=True)
        self.node_tokens = {n: (n.lower(), set(_tokens(n))) for n in G.nodes()}
        self.llm = None
        if config.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.llm = OpenAI(api_key=config.OPENAI_API_KEY)
            except Exception:
                self.llm = None

    def _llm_answer(self, question: str, facts: dict) -> str:
        context_lines = []
        for p in facts["paths"]:
            context_lines.extend(p["steps"])
        for e, nb in facts["neighbors"].items():
            context_lines.extend(nb)
        context = "\n".join(dict.fromkeys(context_lines)) or "(no direct facts found)"

        prompt = (
            "You answer questions about Japan's shipbuilding & green-tech strategy "
            "using ONLY the knowledge-graph facts below. Walk the connections and "
            "explain clearly in 2-4 sentences. If facts are missing, say so.\n\n"
            f"GRAPH FACTS:\n{context}\n\nQUESTION: {question}\n\nANSWER:"
        )
        resp = self.llm.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()

    def answer(self, question: str) -> str:
        """Plain-text answer (used by the CLI)."""
        entities = find_entities(self.G, question, node_tokens=self.node_tokens)
        facts = gather_facts(self.G, entities, UG=self.UG)
        if self.llm is None:
            return _template_answer(question, entities, facts)
        return self._llm_answer(question, facts)

    def answer_structured(self, question: str) -> dict:
        """
        Rich answer for the web API:
          - answer: natural-language text
          - entities: matched node names (to highlight)
          - paths: list of {nodes:[...], steps:[...]} (to draw on the graph)
          - facts: flat fact strings
          - mode: 'llm' or 'offline'
        """
        entities = find_entities(self.G, question, node_tokens=self.node_tokens)
        facts = gather_facts(self.G, entities, UG=self.UG)

        # Build a clean plain-language summary (always available).
        if entities and facts["paths"]:
            story_bits = []
            for step in facts["paths"][0]["steps"]:
                story_bits.append(step.replace(" --", " ").replace("--> ", " "))
            summary = "In plain words: " + "; ".join(story_bits) + "."
        elif entities:
            flat = []
            for nb in facts["neighbors"].values():
                flat.extend(nb)
            summary = ("Direct facts: " + "; ".join(
                s.replace(" --", " ").replace("--> ", " ") for s in flat[:6]) + ".") \
                if flat else "Matched entities have no recorded connections yet."
        else:
            summary = ("I couldn't match anything in your question to the graph. "
                       "Try names like 'Imabari', 'hydrogen', 'offshore wind', "
                       "'7th Energy Plan', or 'emissions'.")

        answer_text = summary
        mode = "offline"
        if self.llm is not None and entities:
            try:
                answer_text = self._llm_answer(question, facts)
                mode = "llm"
            except Exception:
                answer_text = summary

        flat_facts = []
        for p in facts["paths"]:
            flat_facts.extend(p["steps"])
        for nb in facts["neighbors"].values():
            flat_facts.extend(nb)
        flat_facts = list(dict.fromkeys(flat_facts))

        return {
            "question": question,
            "answer": answer_text,
            "summary": summary,
            "entities": entities,
            "paths": [{"nodes": p["path"], "steps": p["steps"]} for p in facts["paths"][:6]],
            "facts": flat_facts[:20],
            "mode": mode,
        }
