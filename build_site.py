#!/usr/bin/env python3
"""
Build a static site from latest.json and recap.json.
"""

from __future__ import annotations

import html
import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SITE_DIR = ROOT / "site"
LATEST_PATH = ROOT / "latest.json"
RECAP_PATH = ROOT / "recap.json"
RECAP_MD_PATH = ROOT / "recap.md"

STYLES = """
:root {
  --bg: #f4efe6;
  --panel: rgba(255, 250, 243, 0.9);
  --panel-strong: #fffaf2;
  --text: #1e1d1a;
  --muted: #685f4e;
  --line: rgba(50, 42, 25, 0.12);
  --accent: #dd5b38;
  --accent-deep: #8f331d;
  --accent-soft: #f6d4bf;
  --tier-a: #264653;
  --tier-b: #2a9d8f;
  --tier-c: #e9c46a;
  --tier-d: #e76f51;
  --shadow: 0 24px 60px rgba(52, 36, 18, 0.12);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  font-family: "Aptos", "Segoe UI", sans-serif;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(221, 91, 56, 0.22), transparent 32%),
    radial-gradient(circle at top right, rgba(38, 70, 83, 0.16), transparent 28%),
    linear-gradient(180deg, #f7f1e8 0%, #efe5d6 100%);
}

a {
  color: inherit;
}

.shell {
  width: min(1120px, calc(100% - 32px));
  margin: 0 auto;
  padding: 32px 0 56px;
}

.hero {
  position: relative;
  overflow: hidden;
  padding: 32px;
  border: 1px solid var(--line);
  border-radius: 28px;
  background: linear-gradient(140deg, rgba(255, 248, 238, 0.96), rgba(249, 234, 216, 0.92));
  box-shadow: var(--shadow);
}

.hero::after {
  content: "";
  position: absolute;
  right: -56px;
  top: -56px;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(221, 91, 56, 0.22), rgba(221, 91, 56, 0));
}

.eyebrow {
  margin: 0 0 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-size: 0.8rem;
  color: var(--accent-deep);
}

h1, h2, h3 {
  font-family: Georgia, "Times New Roman", serif;
  line-height: 1.05;
}

h1 {
  max-width: 14ch;
  margin: 0;
  font-size: clamp(2.8rem, 6vw, 5.6rem);
}

.strapline {
  max-width: 56ch;
  margin: 18px 0 0;
  font-size: 1.08rem;
  line-height: 1.6;
  color: var(--muted);
}

.hero-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 18px;
  margin-top: 28px;
}

.panel {
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--panel);
  padding: 20px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.stat {
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.62);
}

.stat-label {
  margin: 0 0 8px;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
}

.stat-value {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 700;
}

.section {
  margin-top: 24px;
}

.section-title {
  margin: 0 0 14px;
  font-size: 2rem;
}

.two-up {
  display: grid;
  grid-template-columns: 1.3fr 0.9fr;
  gap: 18px;
}

.list {
  display: grid;
  gap: 12px;
}

.highlight {
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.74);
}

.highlight h3 {
  margin: 0 0 8px;
  font-size: 1.1rem;
}

.highlight p, .overview, .bullet-list li {
  margin: 0;
  color: var(--muted);
  line-height: 1.65;
}

.bullet-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
}

.article-groups {
  display: grid;
  gap: 16px;
}

.tier-group {
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 20px;
  background: var(--panel-strong);
  box-shadow: var(--shadow);
}

.tier-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.tier-label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 1.35rem;
}

.swatch {
  width: 14px;
  height: 14px;
  border-radius: 999px;
}

.articles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.article {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  transition: transform 140ms ease, box-shadow 140ms ease;
}

.article:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 36px rgba(48, 35, 17, 0.12);
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 0.82rem;
  color: var(--muted);
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-deep);
  font-weight: 700;
}

.article h3 {
  margin: 0;
  font-size: 1.05rem;
}

.article p {
  margin: 0;
  color: var(--muted);
  line-height: 1.55;
}

.footer {
  margin-top: 24px;
  color: var(--muted);
  font-size: 0.95rem;
}

.footer a {
  color: var(--accent-deep);
}

@media (max-width: 860px) {
  .hero-grid,
  .two-up {
    grid-template-columns: 1fr;
  }

  .stats {
    grid-template-columns: 1fr;
  }

  .shell {
    width: min(100% - 20px, 1120px);
  }

  .hero {
    padding: 22px;
  }
}
"""

TIER_COLORS = {
    "A": "var(--tier-a)",
    "B": "var(--tier-b)",
    "C": "var(--tier-c)",
    "D": "var(--tier-d)",
    "UNKNOWN": "var(--muted)",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_date(value: str | None, fallback: str = "Unknown") -> str:
    if not value:
        return fallback
    normalized = value.replace("Z", "+00:00")
    for parser in (datetime.fromisoformat,):
        try:
            return parser(normalized).strftime("%b %d, %Y")
        except ValueError:
            continue
    return value


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def article_groups(articles: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for article in articles:
        tier = str(article.get("tier", "unknown")).upper()
        grouped[tier].append(article)
    order = {"A": 0, "B": 1, "C": 2, "D": 3, "UNKNOWN": 4}
    return dict(sorted(grouped.items(), key=lambda item: order.get(item[0], 9)))


def render_highlights(recap: dict[str, Any]) -> str:
    items = recap.get("highlights", [])
    if not items:
        return '<div class="highlight"><h3>No highlights yet</h3><p>The latest run did not produce recap highlights.</p></div>'

    blocks = []
    for item in items:
        blocks.append(
            "<article class=\"highlight\">"
            f"<h3>{esc(item.get('title', 'Untitled highlight'))}</h3>"
            f"<p>{esc(item.get('summary', ''))}</p>"
            "</article>"
        )
    return "\n".join(blocks)


def render_list(items: list[str], empty_label: str) -> str:
    if not items:
        return f"<ul class=\"bullet-list\"><li>{esc(empty_label)}</li></ul>"
    return "<ul class=\"bullet-list\">" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def render_articles(articles: list[dict[str, Any]]) -> str:
    if not articles:
        return "<p class=\"overview\">No articles available for this tier yet.</p>"

    cards = []
    for article in articles:
        source = article.get("source", "Unknown source")
        published = format_date(article.get("published"))
        summary = article.get("summary", "").strip() or "Open the source article for the full story."
        cards.append(
            "<a class=\"article\" href=\"{url}\" target=\"_blank\" rel=\"noreferrer\">"
            "<div class=\"meta\">"
            "<span class=\"badge\">{source}</span>"
            "<span>{published}</span>"
            "</div>"
            "<h3>{title}</h3>"
            "<p>{summary}</p>"
            "</a>".format(
                url=esc(article.get("url", "#")),
                source=esc(source),
                published=esc(published),
                title=esc(article.get("title", "Untitled article")),
                summary=esc(summary[:180]),
            )
        )
    return "<div class=\"articles\">" + "".join(cards) + "</div>"


def render_tier_groups(latest: dict[str, Any]) -> str:
    groups = article_groups(latest.get("articles", []))
    if not groups:
        return "<div class=\"tier-group\"><p class=\"overview\">No articles have been collected yet.</p></div>"

    sections = []
    for tier, articles in groups.items():
        color = TIER_COLORS.get(tier, TIER_COLORS["UNKNOWN"])
        sections.append(
            "<section class=\"tier-group\">"
            "<div class=\"tier-head\">"
            "<h3 class=\"tier-label\"><span class=\"swatch\" style=\"background:{color}\"></span>Tier {tier}</h3>"
            "<span class=\"meta\"><span>{count} articles</span></span>"
            "</div>"
            "{articles}"
            "</section>".format(color=color, tier=esc(tier), count=len(articles), articles=render_articles(articles))
        )
    return "\n".join(sections)


def build_index_html(latest: dict[str, Any], recap: dict[str, Any]) -> str:
    article_count = latest.get("article_count", 0)
    source_count = len({article.get("source") for article in latest.get("articles", []) if article.get("source")})
    tier_count = len({str(article.get("tier", "unknown")).upper() for article in latest.get("articles", [])})

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{esc(recap.get("headline", "newsletter4ai"))}</title>
    <meta name="description" content="{esc(recap.get("strapline", "AI news recap"))}">
    <link rel="stylesheet" href="styles.css">
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <p class="eyebrow">newsletter4ai</p>
        <h1>{esc(recap.get("headline", "AI recap"))}</h1>
        <p class="strapline">{esc(recap.get("strapline", ""))}</p>
        <div class="hero-grid">
          <div class="panel">
            <h2 class="section-title">Daily Brief</h2>
            <p class="overview">{esc(recap.get("overview", ""))}</p>
          </div>
          <div class="panel">
            <div class="stats">
              <div class="stat">
                <p class="stat-label">Snapshot</p>
                <p class="stat-value">{esc(recap.get("date_label", "Latest run"))}</p>
              </div>
              <div class="stat">
                <p class="stat-label">Articles</p>
                <p class="stat-value">{article_count}</p>
              </div>
              <div class="stat">
                <p class="stat-label">Sources</p>
                <p class="stat-value">{source_count}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="section two-up">
        <div class="panel">
          <h2 class="section-title">Key Highlights</h2>
          <div class="list">
            {render_highlights(recap)}
          </div>
        </div>
        <div class="list">
          <section class="panel">
            <h2 class="section-title">Watchlist</h2>
            {render_list(recap.get("watchlist", []), "No watchlist items yet.")}
          </section>
          <section class="panel">
            <h2 class="section-title">Themes</h2>
            {render_list(recap.get("themes", []), "No themes available yet.")}
          </section>
          <section class="panel">
            <h2 class="section-title">Coverage</h2>
            <ul class="bullet-list">
              <li>{article_count} articles in the current snapshot.</li>
              <li>{source_count} distinct sources were included.</li>
              <li>{tier_count} source tiers contributed to this run.</li>
            </ul>
          </section>
        </div>
      </section>

      <section class="section article-groups">
        <h2 class="section-title">Source Stream</h2>
        {render_tier_groups(latest)}
      </section>

      <footer class="footer">
        <p>Raw artifacts: <a href="latest.json">latest.json</a> | <a href="recap.json">recap.json</a> | <a href="recap.md">recap.md</a></p>
        <p>Generated with {esc(recap.get("generated_with", "unknown"))} | Source snapshot {esc(recap.get("source_snapshot", "unknown"))}</p>
      </footer>
    </main>
  </body>
</html>
"""


def main() -> None:
    latest = load_json(LATEST_PATH)
    recap = load_json(RECAP_PATH)

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    (SITE_DIR / "styles.css").write_text(STYLES.strip() + "\n", encoding="utf-8")
    (SITE_DIR / "index.html").write_text(build_index_html(latest, recap), encoding="utf-8")
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")

    shutil.copy2(LATEST_PATH, SITE_DIR / "latest.json")
    shutil.copy2(RECAP_PATH, SITE_DIR / "recap.json")
    shutil.copy2(RECAP_MD_PATH, SITE_DIR / "recap.md")

    print(f"Built static site in {SITE_DIR}")


if __name__ == "__main__":
    main()
