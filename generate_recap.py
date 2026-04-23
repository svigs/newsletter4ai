#!/usr/bin/env python3
"""
Generate a daily AI recap from latest.json.

Uses Anthropic's Messages API when ANTHROPIC_API_KEY is set.
Falls back to a deterministic local recap so the pipeline can still build.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ModuleNotFoundError:
    requests = None

ROOT = Path(__file__).resolve().parent
LATEST_PATH = ROOT / "latest.json"
RECAP_JSON_PATH = ROOT / "recap.json"
RECAP_MD_PATH = ROOT / "recap.md"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-opus-4-1-20250805"


def load_latest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def compact_articles(articles: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for article in articles[:limit]:
        compact.append(
            {
                "title": article.get("title", "").strip(),
                "source": article.get("source", "").strip(),
                "tier": article.get("tier", "unknown"),
                "published": article.get("published", ""),
                "summary": article.get("summary", "").strip(),
                "url": article.get("url", "").strip(),
            }
        )
    return compact


def build_prompt(latest: dict[str, Any]) -> str:
    articles = compact_articles(latest.get("articles", []))
    payload = {
        "fetched_at": latest.get("fetched_at"),
        "article_count": latest.get("article_count", len(articles)),
        "articles": articles,
    }
    return (
        "You are generating a concise public AI industry recap for a static newsletter website.\n"
        "Use only the provided articles.\n"
        "Return strict JSON with this shape:\n"
        "{\n"
        '  "headline": string,\n'
        '  "strapline": string,\n'
        '  "overview": string,\n'
        '  "highlights": [{"title": string, "summary": string}],\n'
        '  "watchlist": [string],\n'
        '  "themes": [string]\n'
        "}\n"
        "Rules:\n"
        "- headline under 80 characters\n"
        "- strapline under 140 characters\n"
        "- overview 2 to 4 sentences\n"
        "- highlights length 3 to 5\n"
        "- each highlight summary 1 to 2 sentences\n"
        "- watchlist length 3 to 5\n"
        "- themes length 3 to 5\n"
        "- no markdown, no code fences, no commentary\n\n"
        f"Articles JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def request_claude_recap(latest: dict[str, Any], api_key: str, model: str) -> dict[str, Any]:
    if requests is None:
        raise RuntimeError("requests is required for Claude API calls")
    response = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 1400,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": build_prompt(latest)}],
        },
        timeout=60,
    )
    if response.status_code >= 400:
        # Surface the actual Anthropic error body so we can diagnose 4xx failures.
        raise RuntimeError(
            f"Anthropic API returned HTTP {response.status_code}. "
            f"Model: {model}. Response body: {response.text[:1500]}"
        )
    payload = response.json()
    text_blocks = [
        block.get("text", "")
        for block in payload.get("content", [])
        if block.get("type") == "text"
    ]
    raw_text = "\n".join(part for part in text_blocks if part.strip())
    if not raw_text.strip():
        raise ValueError("Claude response did not contain text content")
    return json.loads(strip_code_fences(raw_text))


def build_fallback_recap(latest: dict[str, Any]) -> dict[str, Any]:
    articles = latest.get("articles", [])
    total_articles = latest.get("article_count", len(articles))
    sources = [article.get("source", "Unknown source") for article in articles if article.get("source")]
    source_count = len(set(sources))
    tier_counts = Counter(article.get("tier", "unknown").upper() for article in articles)

    highlights: list[dict[str, str]] = []
    for article in articles[:5]:
        source = article.get("source", "Unknown source")
        tier = article.get("tier", "unknown").upper()
        summary = article.get("summary", "").strip()
        detail = summary if summary else f"Tracked from {source} in tier {tier}."
        highlights.append({"title": article.get("title", "Untitled article"), "summary": detail})

    watchlist: list[str] = []
    for name, count in Counter(sources).most_common(5):
        watchlist.append(f"{name}: {count} item{'s' if count != 1 else ''} in this run.")

    themes: list[str] = []
    for tier_name in sorted(tier_counts):
        themes.append(f"Tier {tier_name} contributed {tier_counts[tier_name]} stories.")

    fetched_at = parse_timestamp(latest.get("fetched_at"))
    date_label = fetched_at.strftime("%B %d, %Y") if fetched_at else "today"

    return {
        "headline": f"AI recap for {date_label}",
        "strapline": f"{total_articles} articles across {source_count} sources in the latest sweep.",
        "overview": (
            f"This recap was built from {total_articles} collected AI stories. "
            "The summaries below use a deterministic fallback because a Claude response was unavailable."
        ),
        "highlights": highlights or [{"title": "No articles collected", "summary": "The latest run did not return any stories."}],
        "watchlist": watchlist or ["No active watchlist yet because no articles were collected."],
        "themes": themes or ["No theme data yet because no articles were collected."],
    }


def normalize_recap(recap: dict[str, Any], latest: dict[str, Any], generator: str, model: str | None) -> dict[str, Any]:
    highlights = recap.get("highlights") or []
    if not isinstance(highlights, list):
        highlights = []

    normalized_highlights: list[dict[str, str]] = []
    for item in highlights[:5]:
        if isinstance(item, dict):
            title = str(item.get("title", "")).strip()
            summary = str(item.get("summary", "")).strip()
        else:
            title = str(item).strip()
            summary = ""
        if title:
            normalized_highlights.append({"title": title, "summary": summary})

    fetched_at = parse_timestamp(latest.get("fetched_at"))
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "generated_at": generated_at,
        "generated_with": generator,
        "model": model,
        "source_snapshot": latest.get("fetched_at"),
        "date_label": fetched_at.strftime("%A, %B %d, %Y") if fetched_at else "Latest run",
        "article_count": latest.get("article_count", len(latest.get("articles", []))),
        "headline": str(recap.get("headline", "AI recap")).strip() or "AI recap",
        "strapline": str(recap.get("strapline", "")).strip(),
        "overview": str(recap.get("overview", "")).strip(),
        "highlights": normalized_highlights,
        "watchlist": [str(item).strip() for item in (recap.get("watchlist") or []) if str(item).strip()][:5],
        "themes": [str(item).strip() for item in (recap.get("themes") or []) if str(item).strip()][:5],
    }


def render_markdown(recap: dict[str, Any], latest: dict[str, Any]) -> str:
    lines = [
        f"# {recap['headline']}",
        "",
        recap.get("strapline", ""),
        "",
        f"_Generated: {recap['generated_at']}_",
        f"_Source snapshot: {recap.get('source_snapshot', 'unknown')}_",
        "",
        "## Overview",
        "",
        recap.get("overview", ""),
        "",
        "## Highlights",
        "",
    ]

    for item in recap.get("highlights", []):
        lines.append(f"### {item['title']}")
        lines.append("")
        lines.append(item.get("summary", ""))
        lines.append("")

    lines.extend(["## Watchlist", ""])
    for item in recap.get("watchlist", []):
        lines.append(f"- {item}")
    lines.append("")

    lines.extend(["## Themes", ""])
    for item in recap.get("themes", []):
        lines.append(f"- {item}")
    lines.append("")

    lines.extend(["## Source Count", "", f"- Articles collected: {latest.get('article_count', 0)}", ""])
    return "\n".join(lines).strip() + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> None:
    latest = load_latest(LATEST_PATH)
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    model = os.getenv("CLAUDE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    generator = "fallback"
    recap_payload: dict[str, Any]

    if api_key:
        try:
            recap_payload = request_claude_recap(latest, api_key, model)
            generator = "claude"
            print(f"Generated recap with Claude model {model}")
        except Exception as exc:
            print(f"Claude recap failed, switching to fallback: {exc}")
            recap_payload = build_fallback_recap(latest)
    else:
        print("ANTHROPIC_API_KEY not set, using fallback recap")
        recap_payload = build_fallback_recap(latest)

    recap = normalize_recap(recap_payload, latest, generator=generator, model=model if generator == "claude" else None)
    markdown = render_markdown(recap, latest)

    write_json(RECAP_JSON_PATH, recap)
    RECAP_MD_PATH.write_text(markdown, encoding="utf-8")

    print(f"Wrote {RECAP_JSON_PATH.name} and {RECAP_MD_PATH.name}")


if __name__ == "__main__":
    main()
