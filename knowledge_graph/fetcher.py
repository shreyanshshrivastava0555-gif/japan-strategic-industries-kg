"""
Live data fetcher.

Pulls recent news from the web (free, no API key) via Google News RSS, and can
also fetch and clean the readable text of any article URL. The fetched text is
fed into the same extraction -> graph pipeline used for static documents.
"""
import urllib.parse
import warnings
from typing import List

warnings.filterwarnings("ignore", message=".*OpenSSL.*")

import feedparser
import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def fetch_news(query: str, limit: int = 10) -> List[dict]:
    """Return recent news items for a query: title, summary, link, published."""
    url = GOOGLE_NEWS_RSS.format(q=urllib.parse.quote(query))
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        summary = entry.get("summary", "")
        if summary:
            summary = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)
        items.append({
            "title": entry.get("title", "").strip(),
            "summary": summary,
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "source": entry.get("source", {}).get("title", "") if entry.get("source") else "",
        })
    return items


def fetch_all_news(queries: List[str], per_query: int = 8) -> List[dict]:
    """Fetch news for several queries and de-duplicate by title."""
    seen = set()
    all_items = []
    for q in queries:
        for it in fetch_news(q, limit=per_query):
            key = it["title"].lower()
            if key and key not in seen:
                seen.add(key)
                all_items.append(it)
    return all_items


def fetch_article_text(url: str, max_chars: int = 6000) -> str:
    """Download an article and return cleaned readable text (best-effort)."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return f"[could not fetch {url}: {e}]"
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    text = "\n".join(p for p in paragraphs if len(p) > 40)
    return text[:max_chars]


def news_to_text(items: List[dict]) -> str:
    """Flatten news items into one text blob for LLM extraction."""
    blocks = []
    for it in items:
        blocks.append(f"{it['title']}. {it['summary']} (source: {it.get('source','')})")
    return "\n".join(blocks)
