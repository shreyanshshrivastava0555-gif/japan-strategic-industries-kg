"""Central configuration for the Knowledge Graph Builder Agent."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
OUTPUT_DIR = os.path.join(HERE, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# LLM settings. The agent reads the API key from the environment.
# If no key is present, it automatically falls back to the offline extractor.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.environ.get("KG_MODEL", "gpt-4o-mini")

# Node category -> color, used everywhere for consistent visuals.
CATEGORY_COLORS = {
    "company": "#4C72B0",      # blue
    "technology": "#55A868",   # green
    "policy": "#C44E52",       # red
    "target": "#8172B3",       # purple
    "sector": "#CCB974",       # gold
    "organization": "#64B5CD", # cyan
    "country": "#937860",      # brown
    "news": "#E8A33D",         # orange (live web data)
    "concept": "#999999",      # grey
}

# Default topics the live fetcher searches for (Japan study scope).
LIVE_QUERIES = [
    "Japan shipbuilding Imabari JMU consolidation",
    "Japan offshore wind capacity target",
    "Japan hydrogen ammonia energy policy",
    "Japan green technology decarbonization 2035",
]
DEFAULT_COLOR = "#999999"
