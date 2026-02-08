#!/usr/bin/env python3
"""
ENTROPY SURVIVOR - Worldview Synthesis Engine
Processes raw alpha into worldview updates and trade signals.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import re

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ALPHA_FILE = DATA_DIR / "alpha.jsonl"
WORLDVIEW_FILE = DATA_DIR / "worldview.json"
SOURCE_WEIGHTS_FILE = DATA_DIR / "source_weights.json"
STATE_HISTORY_FILE = BASE_DIR / "logs" / "state_history.jsonl"

# Keywords for signal extraction
BULLISH_KEYWORDS = [
    'bullish', 'long', 'buy', 'calls', 'breakout', 'moon', 'pump',
    'undervalued', 'accumulate', 'upside', 'rally', 'green', 'rip',
    'alpha', 'opportunity', 'gem', 'cheap', 'oversold'
]

BEARISH_KEYWORDS = [
    'bearish', 'short', 'sell', 'puts', 'breakdown', 'dump', 'crash',
    'overvalued', 'distribute', 'downside', 'correction', 'red', 'fade',
    'warning', 'exit', 'expensive', 'overbought', 'top'
]

ASSET_PATTERNS = [
    r'\$([A-Z]{1,5})\b',  # Ticker symbols like $SNAP
    r'\b(BTC|ETH|SOL|AVAX|MATIC|LINK|UNI|AAVE|SNX)\b',  # Crypto
    r'\b(Bitcoin|Ethereum|Solana)\b',  # Crypto full names
]

# Load files
def load_worldview():
    if WORLDVIEW_FILE.exists():
        with open(WORLDVIEW_FILE) as f:
            return json.load(f)
    return None

def load_source_weights():
    with open(SOURCE_WEIGHTS_FILE) as f:
        return json.load(f)

def load_unprocessed_alphas():
    """Load alphas that haven't been processed for synthesis"""
    if not ALPHA_FILE.exists():
        return []
    
    alphas = []
    with open(ALPHA_FILE) as f:
        for line in f:
            if line.strip():
                alpha = json.loads(line)
                if alpha.get('extracted_signal') is None:
                    alphas.append(alpha)
    return alphas

# Signal extraction
def extract_signal(alpha, source_weights):
    """Extract trading signal from alpha content"""
    content = (alpha.get('raw_content') or '').lower()
    
    # Count bullish/bearish signals
    bullish_score = sum(1 for kw in BULLISH_KEYWORDS if kw in content)
    bearish_score = sum(1 for kw in BEARISH_KEYWORDS if kw in content)
    
    # Determine direction
    if bullish_score > bearish_score + 1:
        direction = 'long'
    elif bearish_score > bullish_score + 1:
        direction = 'short'
    else:
        direction = 'neutral'
    
    # Extract asset mentions
    assets = []
    for pattern in ASSET_PATTERNS:
        matches = re.findall(pattern, alpha.get('raw_content') or '', re.IGNORECASE)
        assets.extend([m.upper() for m in matches])
    assets = list(set(assets))
    
    # Calculate confidence based on source trust and signal strength
    source_id = alpha.get('source_id', '')
    source_trust = 0.5  # Default
    
    all_sources = (
        source_weights['sources'].get('twitter', []) +
        source_weights['sources'].get('substack', []) +
        source_weights['sources'].get('telegram', []) +
        source_weights['sources'].get('websites', [])
    )
    
    for src in all_sources:
        if src.get('id') == source_id:
            source_trust = src.get('trust', 0.5)
            break
    
    signal_strength = max(bullish_score, bearish_score) / 5.0  # Normalize
    signal_strength = min(signal_strength, 1.0)
    
    confidence = source_trust * 0.6 + signal_strength * 0.4
    confidence = min(max(confidence, 0.1), 0.95)
    
    return {
        'direction': direction,
        'asset': assets[0] if assets else None,
        'all_assets': assets,
        'confidence': round(confidence, 3),
        'bullish_signals': bullish_score,
        'bearish_signals': bearish_score,
        'source_trust': source_trust
    }

# Update alpha with extracted signal
def update_alpha_with_signal(alpha_id, signal):
    """Update the alpha file with extracted signal"""
    lines = []
    with open(ALPHA_FILE) as f:
        for line in f:
            if line.strip():
                alpha = json.loads(line)
                if alpha.get('id') == alpha_id:
                    alpha['extracted_signal'] = signal
                    alpha['processed_at'] = datetime.now(timezone.utc).isoformat()
                lines.append(json.dumps(alpha))
    
    with open(ALPHA_FILE, 'w') as f:
        f.write('\n'.join(lines) + '\n')

# Worldview update logic
def update_worldview(worldview, processed_alphas):
    """Update worldview based on new alpha signals"""
    if not processed_alphas:
        return worldview, False
    
    changed = False
    
    # Generate new state ID
    new_state_id = f"state_{hashlib.md5(datetime.now(timezone.utc).isoformat().encode()).hexdigest()[:8]}"
    
    # Aggregate signals by sector
    sector_signals = {
        'social_media': [],
        'crypto_ai': [],
        'defi': [],
        'trad_equities': [],
        'options': []
    }
    
    # Map assets to sectors
    crypto_assets = ['BTC', 'ETH', 'SOL', 'AVAX', 'MATIC', 'LINK', 'UNI', 'AAVE', 'SNX', 'BITCOIN', 'ETHEREUM', 'SOLANA']
    defi_assets = ['UNI', 'AAVE', 'SNX', 'SUSHI', 'CRV', 'MKR', 'COMP']
    social_assets = ['SNAP', 'META', 'TWTR', 'PINS', 'RDDT']
    
    for alpha in processed_alphas:
        signal = alpha.get('extracted_signal', {})
        if not signal:
            continue
        
        assets = signal.get('all_assets', [])
        direction = signal.get('direction', 'neutral')
        confidence = signal.get('confidence', 0.5)
        
        # Categorize signal
        for asset in assets:
            asset_upper = asset.upper()
            if asset_upper in crypto_assets:
                sector_signals['crypto_ai'].append((direction, confidence))
            if asset_upper in defi_assets:
                sector_signals['defi'].append((direction, confidence))
            if asset_upper in social_assets:
                sector_signals['social_media'].append((direction, confidence))
            # Default to equities if not crypto
            if asset_upper not in crypto_assets:
                sector_signals['trad_equities'].append((direction, confidence))
    
    # Update sector views
    for sector, signals in sector_signals.items():
        if signals:
            bullish_weight = sum(c for d, c in signals if d == 'long')
            bearish_weight = sum(c for d, c in signals if d == 'short')
            total = bullish_weight + bearish_weight
            
            if total > 0:
                new_confidence = max(bullish_weight, bearish_weight) / (total + 1)
                new_confidence = min(max(new_confidence, 0.3), 0.9)
                
                if bullish_weight > bearish_weight * 1.2:
                    new_stance = 'bullish'
                elif bearish_weight > bullish_weight * 1.2:
                    new_stance = 'bearish'
                else:
                    new_stance = 'neutral'
                
                old_conf = worldview['sector_views'][sector]['confidence']
                worldview['sector_views'][sector] = {
                    'stance': new_stance,
                    'confidence': round(old_conf * 0.7 + new_confidence * 0.3, 3)  # Smoothing
                }
                changed = True
    
    # Create/update active theses from strong signals
    for alpha in processed_alphas:
        signal = alpha.get('extracted_signal', {})
        if signal.get('confidence', 0) > 0.7 and signal.get('asset'):
            # Check if thesis already exists for this asset
            existing = None
            for thesis in worldview.get('active_theses', []):
                if thesis.get('asset') == signal['asset']:
                    existing = thesis
                    break
            
            if existing:
                # Update existing thesis
                existing['confidence'] = round(
                    existing['confidence'] * 0.6 + signal['confidence'] * 0.4, 3
                )
                if alpha['source'] not in existing.get('sources', []):
                    existing['sources'].append(alpha['source'])
                existing['last_updated'] = datetime.now(timezone.utc).isoformat()
                changed = True
            elif signal['direction'] != 'neutral':
                # Create new thesis
                new_thesis = {
                    'id': f"thesis_{signal['asset'].lower()}_{hashlib.md5(datetime.now(timezone.utc).isoformat().encode()).hexdigest()[:6]}",
                    'asset': signal['asset'],
                    'thesis': f"{signal['direction'].upper()} {signal['asset']} based on alpha signals",
                    'direction': signal['direction'],
                    'confidence': signal['confidence'],
                    'sources': [alpha['source']],
                    'created': datetime.now(timezone.utc).isoformat(),
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'status': 'watching'
                }
                worldview['active_theses'].append(new_thesis)
                changed = True
    
    if changed:
        worldview['state_id'] = new_state_id
        worldview['last_updated'] = datetime.now(timezone.utc).isoformat()
        worldview['version'] = worldview.get('version', 0) + 1
    
    return worldview, changed

# Save worldview and log state
def save_worldview(worldview, log_state=True):
    with open(WORLDVIEW_FILE, 'w') as f:
        json.dump(worldview, f, indent=2)
    
    if log_state:
        state_log = {
            'state_id': worldview['state_id'],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'snapshot': worldview
        }
        with open(STATE_HISTORY_FILE, 'a') as f:
            f.write(json.dumps(state_log) + '\n')

# Main synthesis
def run_synthesis():
    print(f"\n{'='*60}")
    print(f"ENTROPY SURVIVOR - WORLDVIEW SYNTHESIS")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")
    
    worldview = load_worldview()
    if not worldview:
        print("[-] No worldview found!")
        return
    
    source_weights = load_source_weights()
    unprocessed = load_unprocessed_alphas()
    
    print(f"[*] Worldview state: {worldview.get('state_id', 'unknown')}")
    print(f"[*] Unprocessed alphas: {len(unprocessed)}")
    
    # Extract signals from unprocessed alphas
    processed = []
    for alpha in unprocessed:
        signal = extract_signal(alpha, source_weights)
        update_alpha_with_signal(alpha['id'], signal)
        alpha['extracted_signal'] = signal
        processed.append(alpha)
        
        direction = signal.get('direction', 'neutral')
        asset = signal.get('asset', 'N/A')
        confidence = signal.get('confidence', 0)
        print(f"    -> {alpha['source']}: {direction.upper()} {asset} ({confidence:.0%})")
    
    # Update worldview
    print(f"\n[*] Updating worldview...")
    worldview, changed = update_worldview(worldview, processed)
    
    if changed:
        save_worldview(worldview, log_state=True)
        print(f"[+] Worldview updated: {worldview['state_id']}")
    else:
        print("[=] No worldview changes")
    
    print(f"\n{'='*60}")
    print(f"SYNTHESIS COMPLETE")
    print(f"Processed: {len(processed)} alphas")
    print(f"Active theses: {len(worldview.get('active_theses', []))}")
    print(f"{'='*60}\n")
    
    return worldview

if __name__ == "__main__":
    run_synthesis()
