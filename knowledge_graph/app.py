"""
Knowledge Graph Builder Agent - command line interface.

Examples:
    python app.py build                      # build graph from the Japan brief
    python app.py build --input mydoc.txt    # build from your own document
    python app.py ask "How does Imabari connect to Japan's emissions goal?"
    python app.py chat                        # interactive Q&A session
    python app.py stats                       # show graph statistics
"""
import argparse
import os
import sys

import config
import extractor as extractor_mod
import graph as graph_mod
import visualize
from query import GraphQueryAgent


DEFAULT_INPUT = os.path.join(config.DATA_DIR, "japan_brief.txt")
GRAPH_PATH = os.path.join(config.OUTPUT_DIR, "graph.json")


def cmd_build(args):
    input_path = args.input or DEFAULT_INPUT
    if not os.path.exists(input_path):
        print(f"[!] Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path) as f:
        text = f.read()

    ext, mode = extractor_mod.get_extractor(force_offline=args.offline)
    print(f"[*] Extractor mode: {mode.upper()}"
          + ("  (set OPENAI_API_KEY to use the live LLM)" if mode == "offline" else ""))

    triples = ext.extract(text)
    print(f"[*] Extracted {len(triples)} triples.")

    G = graph_mod.build_graph(triples)
    graph_mod.save_graph(G, GRAPH_PATH)
    print(f"[*] Graph saved: {GRAPH_PATH}")

    html = visualize.to_html(G)
    png = visualize.to_png(G)
    print(f"[*] Interactive view: {html}")
    print(f"[*] Static image:     {png}")

    _print_stats(G)


def cmd_fetch(args):
    import fetcher
    import config as cfg

    queries = [args.query] if args.query else cfg.LIVE_QUERIES
    print(f"[*] Fetching live news for {len(queries)} topic(s)...")
    items = fetcher.fetch_all_news(queries, per_query=args.per_query)
    print(f"[*] Retrieved {len(items)} unique news items from the web.")

    if not items:
        print("[!] No items returned (check your internet connection).")
        sys.exit(1)

    # Show a few headlines so the user sees the live data.
    print("\n--- Sample live headlines ---")
    for it in items[:6]:
        src = f" [{it['source']}]" if it.get("source") else ""
        print(f"  - {it['title']}{src}")
    print()

    # Extract triples from the live data.
    ext, mode = extractor_mod.get_extractor(force_offline=args.offline)
    print(f"[*] Extractor mode: {mode.upper()}")
    if mode == "llm":
        triples = ext.extract(fetcher.news_to_text(items))
    else:
        triples = extractor_mod.mine_news_triples(items)
    print(f"[*] Extracted {len(triples)} live triples.")

    # Start from existing graph (if any) unless --fresh is given.
    if os.path.exists(GRAPH_PATH) and not args.fresh:
        G = graph_mod.load_graph(GRAPH_PATH)
        print("[*] Merging live data into the existing graph.")
    else:
        G = graph_mod.build_graph([])
        print("[*] Building a fresh graph from live data only.")

    graph_mod.merge_triples(G, triples)
    graph_mod.save_graph(G, GRAPH_PATH)
    visualize.to_html(G)
    visualize.to_png(G)
    print(f"[*] Graph updated and re-rendered in {config.OUTPUT_DIR}")
    _print_stats(G)


def _print_stats(G):
    s = graph_mod.graph_stats(G)
    print("\n=== Graph statistics ===")
    print(f"  Nodes: {s['nodes']}   Edges: {s['edges']}")
    print("  By category: " + ", ".join(f"{k}={v}" for k, v in sorted(s["by_category"].items())))
    print("  Top hubs (most connected):")
    for name, deg in s["top_hubs"]:
        print(f"    - {name} ({deg} connections)")


def cmd_stats(args):
    if not os.path.exists(GRAPH_PATH):
        print("[!] No graph found. Run 'python app.py build' first.")
        sys.exit(1)
    G = graph_mod.load_graph(GRAPH_PATH)
    _print_stats(G)


def _load_agent():
    if not os.path.exists(GRAPH_PATH):
        print("[!] No graph found. Run 'python app.py build' first.")
        sys.exit(1)
    G = graph_mod.load_graph(GRAPH_PATH)
    return GraphQueryAgent(G)


def cmd_ask(args):
    agent = _load_agent()
    print(agent.answer(args.question))


def cmd_chat(args):
    agent = _load_agent()
    print("Knowledge Graph Chat. Ask about Japan's shipbuilding & green tech.")
    print("Type 'exit' or 'quit' to leave.\n")
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if q.lower() in {"exit", "quit"}:
            break
        if not q:
            continue
        print("\n" + agent.answer(q) + "\n")


def main():
    p = argparse.ArgumentParser(description="Knowledge Graph Builder Agent")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Build the knowledge graph from a document")
    b.add_argument("--input", help="Path to a text file (defaults to the Japan brief)")
    b.add_argument("--offline", action="store_true", help="Force the offline extractor")
    b.set_defaults(func=cmd_build)

    fp = sub.add_parser("fetch", help="Fetch live news from the web and update the graph")
    fp.add_argument("--query", help="Custom search query (defaults to the study topics)")
    fp.add_argument("--per-query", type=int, default=8, help="Items per query (default 8)")
    fp.add_argument("--fresh", action="store_true", help="Ignore existing graph, build from live data only")
    fp.add_argument("--offline", action="store_true", help="Force the offline extractor")
    fp.set_defaults(func=cmd_fetch)

    a = sub.add_parser("ask", help="Ask a single question")
    a.add_argument("question", help="Your question in quotes")
    a.set_defaults(func=cmd_ask)

    c = sub.add_parser("chat", help="Interactive Q&A")
    c.set_defaults(func=cmd_chat)

    s = sub.add_parser("stats", help="Show graph statistics")
    s.set_defaults(func=cmd_stats)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
