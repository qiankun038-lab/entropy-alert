#!/usr/bin/env python3
"""
ENTROPY SURVIVOR - Alpha Ingestion System
Fetches content from Twitter, Substack, Telegram, and websites.
"""

import json
import os
import sys
import hashlib
import requests
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
import re
import time

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ALPHA_FILE = DATA_DIR / "alpha.jsonl"
SOURCE_WEIGHTS_FILE = DATA_DIR / "source_weights.json"
STATE_HISTORY_FILE = BASE_DIR / "logs" / "state_history.jsonl"

# Load source config
def load_sources():
    with open(SOURCE_WEIGHTS_FILE) as f:
        return json.load(f)

# Generate unique ID for alpha
def generate_alpha_id(source, content, timestamp):
    hash_input = f"{source}:{content[:100]}:{timestamp}"
    return f"alpha_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"

# Check if alpha already exists
def alpha_exists(alpha_id):
    if not ALPHA_FILE.exists():
        return False
    with open(ALPHA_FILE) as f:
        for line in f:
            if line.strip():
                alpha = json.loads(line)
                if alpha.get('id') == alpha_id:
                    return True
    return False

# Save alpha
def save_alpha(alpha):
    with open(ALPHA_FILE, 'a') as f:
        f.write(json.dumps(alpha) + '\n')
    print(f"[+] Saved alpha: {alpha['id']} from {alpha['source']}")

# Fetch RSS feed
def fetch_rss(url, source_name, source_id, source_type="substack"):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; EntropySurvivor/1.0)'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
        
        alphas = []
        for item in items[:10]:  # Last 10 items
            # Handle both RSS and Atom feeds
            title = item.find('title')
            title = title.text if title is not None else ''
            
            description = item.find('description')
            if description is None:
                description = item.find('{http://www.w3.org/2005/Atom}content')
            content = description.text if description is not None else ''
            
            # Clean HTML from content
            content = re.sub(r'<[^>]+>', '', content or '')[:1000]
            
            pub_date = item.find('pubDate')
            if pub_date is None:
                pub_date = item.find('{http://www.w3.org/2005/Atom}published')
            timestamp = pub_date.text if pub_date is not None else datetime.now(timezone.utc).isoformat()
            
            link = item.find('link')
            if link is None:
                link = item.find('{http://www.w3.org/2005/Atom}link')
                url = link.get('href') if link is not None else ''
            else:
                url = link.text or ''
            
            alpha_id = generate_alpha_id(source_id, title + content, timestamp)
            
            if not alpha_exists(alpha_id):
                alpha = {
                    'id': alpha_id,
                    'source': source_name,
                    'source_id': source_id,
                    'source_type': source_type,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'ingested_at': datetime.now(timezone.utc).isoformat(),
                    'title': title,
                    'raw_content': f"{title}\n\n{content}",
                    'url': url,
                    'extracted_signal': None  # Will be filled by synthesis
                }
                alphas.append(alpha)
        
        return alphas
    except Exception as e:
        print(f"[-] Error fetching RSS {url}: {e}")
        return []

# Fetch Twitter via Nitter
def fetch_twitter_nitter(handle, source_id):
    """Fetch tweets via Nitter RSS feed"""
    nitter_instances = [
        "nitter.net",
        "nitter.poast.org",
        "nitter.privacydev.net",
        "nitter.1d4.us"
    ]
    
    handle_clean = handle.lstrip('@')
    
    for instance in nitter_instances:
        try:
            url = f"https://{instance}/{handle_clean}/rss"
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; EntropySurvivor/1.0)'}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                
                alphas = []
                for item in items[:10]:
                    title = item.find('title')
                    title_text = title.text if title is not None else ''
                    
                    description = item.find('description')
                    content = description.text if description is not None else ''
                    content = re.sub(r'<[^>]+>', '', content or '')
                    
                    pub_date = item.find('pubDate')
                    timestamp = pub_date.text if pub_date is not None else datetime.now(timezone.utc).isoformat()
                    
                    link = item.find('link')
                    tweet_url = link.text if link is not None else ''
                    
                    full_content = f"{title_text}\n{content}".strip()
                    alpha_id = generate_alpha_id(source_id, full_content, timestamp)
                    
                    if not alpha_exists(alpha_id):
                        alpha = {
                            'id': alpha_id,
                            'source': handle,
                            'source_id': source_id,
                            'source_type': 'twitter',
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'ingested_at': datetime.now(timezone.utc).isoformat(),
                            'raw_content': full_content,
                            'url': tweet_url,
                            'extracted_signal': None
                        }
                        alphas.append(alpha)
                
                return alphas
        except Exception as e:
            print(f"[-] Nitter {instance} failed for {handle}: {e}")
            continue
    
    print(f"[-] All Nitter instances failed for {handle}")
    return []

# Fetch website content
def fetch_website(url, source_name, source_id):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; EntropySurvivor/1.0)'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Simple text extraction
        content = re.sub(r'<script[^>]*>.*?</script>', '', response.text, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()[:2000]
        
        alpha_id = generate_alpha_id(source_id, content, datetime.now(timezone.utc).isoformat())
        
        if not alpha_exists(alpha_id):
            alpha = {
                'id': alpha_id,
                'source': source_name,
                'source_id': source_id,
                'source_type': 'website',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'ingested_at': datetime.now(timezone.utc).isoformat(),
                'raw_content': content,
                'url': url,
                'extracted_signal': None
            }
            return [alpha]
        return []
    except Exception as e:
        print(f"[-] Error fetching website {url}: {e}")
        return []

# Main ingestion
def run_ingestion():
    print(f"\n{'='*60}")
    print(f"ENTROPY SURVIVOR - ALPHA INGESTION")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")
    
    sources = load_sources()
    all_alphas = []
    
    # Twitter
    print("[*] Fetching Twitter sources...")
    for source in sources['sources']['twitter']:
        print(f"    -> {source['handle']}")
        alphas = fetch_twitter_nitter(source['handle'], source['id'])
        all_alphas.extend(alphas)
        time.sleep(1)  # Rate limiting
    
    # Substack
    print("\n[*] Fetching Substack sources...")
    for source in sources['sources']['substack']:
        print(f"    -> {source['name']}")
        alphas = fetch_rss(source['rss'], source['name'], source['id'], 'substack')
        all_alphas.extend(alphas)
        time.sleep(1)
    
    # Websites
    print("\n[*] Fetching website sources...")
    for source in sources['sources']['websites']:
        print(f"    -> {source['name']}")
        alphas = fetch_website(source['url'], source['name'], source['id'])
        all_alphas.extend(alphas)
        time.sleep(1)
    
    # Save all new alphas
    print(f"\n[*] Saving {len(all_alphas)} new alpha signals...")
    for alpha in all_alphas:
        save_alpha(alpha)
    
    print(f"\n{'='*60}")
    print(f"INGESTION COMPLETE")
    print(f"New alphas: {len(all_alphas)}")
    print(f"Finished: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")
    
    return len(all_alphas)

if __name__ == "__main__":
    run_ingestion()
