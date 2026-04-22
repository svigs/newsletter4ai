# newsletter4ai

Scheduled AI-news collector. A GitHub Action runs twice a day, fetches a curated set of RSS feeds and HackerNews queries, and commits the result to `latest.json`. A claude.ai routine then reads `latest.json` and synthesizes a digest.

## Schedule

Cron runs in UTC. `0 6 * * *` and `0 18 * * *` = 08:00 / 20:00 Europe/Ljubljana in summer (CEST, UTC+2), and 07:00 / 19:00 in winter (CET, UTC+1).

## Files

- `feeds.json` — source config, organized by tier:
  - `tier_a` — frontier labs (Google, DeepMind, OpenAI, Anthropic, NVIDIA, Meta, Microsoft, Mistral, Cohere, Perplexity)
  - `tier_b` — broader coverage (Hugging Face, MIT Tech Review, The Verge AI, VentureBeat AI)
  - `tier_c` — HackerNews Algolia queries for companies without reliable RSS (xAI/Grok, DeepSeek, Qwen/Alibaba, and HN backup for Perplexity/Mistral)
- `collector.py` — fetches every source, dedupes by URL, sorts by date, writes `latest.json`
- `.github/workflows/fetch.yml` — schedule + `workflow_dispatch` + auto-run on edits to `collector.py` / `feeds.json` / the workflow
- `latest.json` — most recent snapshot (auto-updated by the Action)

## Run locally

```bash
pip install feedparser requests
python collector.py
```

## Manual trigger

Actions tab → "Fetch AI News" → "Run workflow". Or push an edit to `collector.py` / `feeds.json` — the workflow auto-runs.

## Tuning

- Add / remove sources in `feeds.json`.
- Change the schedule in `.github/workflows/fetch.yml`.
- To change the HN lookback window, edit the `hours=` arg in `main()` of `collector.py`.
