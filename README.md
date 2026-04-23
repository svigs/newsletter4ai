# newsletter4ai

Scheduled AI-news collector and recap pipeline. A GitHub Action runs twice a day, fetches a curated set of RSS feeds and Hacker News queries, writes `latest.json`, generates a Claude recap, and deploys a static site.

## Schedule

Cron runs in UTC. `0 6 * * *` and `0 18 * * *` = 08:00 / 20:00 Europe/Ljubljana in summer (CEST, UTC+2), and 07:00 / 19:00 in winter (CET, UTC+1).

## Files

- `feeds.json` - source config, organized by tier
- `collector.py` - fetches sources, dedupes by URL, sorts by date, writes `latest.json`
- `generate_recap.py` - reads `latest.json`, calls Claude when configured, writes `recap.json` and `recap.md`
- `build_site.py` - builds the static site into `site/`
- `.github/workflows/fetch.yml` - scheduled workflow, recap generation, Pages deploy
- `latest.json` - most recent raw snapshot
- `recap.json` - structured recap for the site
- `recap.md` - markdown recap artifact

## Run locally

```bash
pip install -r requirements.txt
python collector.py
python generate_recap.py
python build_site.py
```

## Manual trigger

Actions tab -> "Build newsletter4ai" -> "Run workflow".

## Tuning

- Add or remove sources in `feeds.json`
- Change the schedule in `.github/workflows/fetch.yml`
- Change the Claude model with the `CLAUDE_MODEL` GitHub Actions variable
