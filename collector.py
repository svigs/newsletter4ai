#!/usr/bin/env python3
"""
Fetch AI news from RSS feeds and HN Algolia API.
Outputs to latest.json with deduplication and timestamp.
"""

import json
import feedparser
import requests
from datetime import datetime, timedelta
import time

def load_feeds_config():
    """Load feeds configuration from feeds.json"""
    with open('feeds.json', 'r') as f:
        return json.load(f)

def fetch_rss_feed(url, source_name):
    """Fetch and parse a single RSS feed"""
    articles = []
    try:
        feed = feedparser.parse(url)
        
        if feed.bozo:
            print(f"⚠️  Warning parsing {source_name}: {feed.bozo_exception}")
        
        for entry in feed.entries[:10]:  # Limit to 10 per feed
            article = {
                'title': entry.get('title', 'No title'),
                'url': entry.get('link', ''),
                'source': source_name,
                'published': entry.get('published', entry.get('updated', '')),
                'summary': entry.get('summary', '')[:200] if entry.get('summary') else '',
                'tier': 'unknown'
            }
            if article['url']:  # Only add if has URL
                articles.append(article)
    except Exception as e:
        print(f"❌ Error fetching {source_name}: {e}")
    
    return articles

def fetch_hn_algolia(query, source_name, hours=24):
    """Fetch from HN Algolia API with timestamp filter"""
    articles = []
    try:
        # Calculate timestamp for N hours ago
        timestamp = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
        url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&numericFilters=created_at_i>{timestamp}&hitsPerPage=10"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for hit in data.get('hits', [])[:10]:
            article = {
                'title': hit.get('title', 'No title'),
                'url': hit.get('url', f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                'source': source_name,
                'published': datetime.fromtimestamp(hit.get('created_at_i', 0)).isoformat(),
                'summary': '',
                'tier': 'unknown'
            }
            articles.append(article)
    except Exception as e:
        print(f"❌ Error fetching {source_name}: {e}")
    
    return articles

def deduplicate_articles(articles):
    """Remove duplicate articles by URL"""
    seen_urls = set()
    unique = []
    
    for article in articles:
        url = article.get('url', '').lower()
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(article)
    
    return unique

def assign_tiers(articles, feeds_config):
    """Assign tier information based on source"""
    tier_map = {}
    
    # Build tier map from feeds.json structure
    for tier_key, tier_data in feeds_config.items():
        tier_letter = tier_key.replace('tier_', '')
        if isinstance(tier_data, dict):
            for source in tier_data.keys():
                tier_map[source] = tier_letter
    
    for article in articles:
        article['tier'] = tier_map.get(article['source'], 'unknown')
    
    return articles

def main():
    print("🚀 Starting AI news fetch...")
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}Z")
    
    feeds_config = load_feeds_config()
    all_articles = []
    
    # Fetch Tier A feeds (most reliable)
    print("\n📡 Fetching Tier A feeds...")
    for source, url in feeds_config['tier_a'].items():
        articles = fetch_rss_feed(url, source)
        all_articles.extend(articles)
        print(f"  ✓ {source}: {len(articles)} articles")
        time.sleep(0.5)  # Be nice to servers
    
    # Fetch Tier B feeds
    print("📡 Fetching Tier B feeds...")
    for source, url in feeds_config['tier_b'].items():
        articles = fetch_rss_feed(url, source)
        all_articles.extend(articles)
        print(f"  ✓ {source}: {len(articles)} articles")
        time.sleep(0.5)
    
    # Fetch Tier D feeds
    print("📡 Fetching Tier D feeds...")
    for source, url in feeds_config['tier_d'].items():
        articles = fetch_rss_feed(url, source)
        all_articles.extend(articles)
        print(f"  ✓ {source}: {len(articles)} articles")
        time.sleep(0.5)
    
    # Fetch Tier C (HN Algolia) - manual queries
    print("📡 Fetching Tier C (HN Algolia)...")
    hn_queries = {
        "xAI Grok": "xai+grok",
        "DeepSeek": "deepseek",
        "Qwen/Alibaba": "qwen+alibaba",
        "Perplexity": "perplexity+ai",
        "Mistral": "mistral+ai"
    }
    for query_name, query in hn_queries.items():
        source = f"HN - {query_name}"
        articles = fetch_hn_algolia(query, source, hours=24)
        all_articles.extend(articles)
        print(f"  ✓ {source}: {len(articles)} articles")
        time.sleep(0.5)
    
    # Post-processing
    print(f"\n✅ Fetched {len(all_articles)} articles before deduplication")
    
    all_articles = deduplicate_articles(all_articles)
    print(f"✅ {len(all_articles)} unique articles after deduplication")
    
    all_articles = assign_tiers(all_articles, feeds_config)
    
    # Sort by published date (newest first), handling missing dates
    all_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
    
    # Prepare output
    output = {
        'fetched_at': datetime.utcnow().isoformat() + 'Z',
        'article_count': len(all_articles),
        'articles': all_articles
    }
    
    # Write to latest.json
    with open('latest.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Saved {len(all_articles)} articles to latest.json")
    print("✨ Done!")

if __name__ == '__main__':
    main()
