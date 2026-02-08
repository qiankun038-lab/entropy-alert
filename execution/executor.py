#!/usr/bin/env python3
"""
ENTROPY SURVIVOR - Trade Execution Engine
Generates and executes trades based on worldview theses.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import hashlib

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
WORLDVIEW_FILE = DATA_DIR / "worldview.json"
TRADES_FILE = DATA_DIR / "trades.jsonl"
SIGNALS_FILE = DATA_DIR / "pending_signals.json"

# ACP Configuration
ACP_WALLET = "0x19259e95855cD1f167ebBbe2836Bc62ac3B99c1B"
ACP_AGENTS = {
    "ethy-ai": {
        "name": "Ethy AI",
        "supported_assets": ["crypto"],
        "networks": ["base", "ethereum"]
    }
}

# Portfolio state
def load_portfolio():
    """Load current portfolio state"""
    portfolio_file = DATA_DIR / "portfolio.json"
    if portfolio_file.exists():
        with open(portfolio_file) as f:
            return json.load(f)
    return {
        "total_value_usd": 2084.58,
        "high_water_mark": 2084.58,
        "positions": [],
        "realized_pnl": 0,
        "unrealized_pnl": 0,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

def save_portfolio(portfolio):
    portfolio_file = DATA_DIR / "portfolio.json"
    portfolio["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(portfolio_file, 'w') as f:
        json.dump(portfolio, f, indent=2)

def load_worldview():
    with open(WORLDVIEW_FILE) as f:
        return json.load(f)

def load_trades():
    if not TRADES_FILE.exists():
        return []
    trades = []
    with open(TRADES_FILE) as f:
        for line in f:
            if line.strip():
                trades.append(json.loads(line))
    return trades

def save_trade(trade):
    with open(TRADES_FILE, 'a') as f:
        f.write(json.dumps(trade) + '\n')

# Risk checks
def check_drawdown(portfolio, risk_params):
    """Check if current drawdown exceeds limit"""
    hwm = portfolio.get('high_water_mark', portfolio['total_value_usd'])
    current = portfolio['total_value_usd']
    drawdown = (hwm - current) / hwm * 100 if hwm > 0 else 0
    max_drawdown = risk_params.get('max_drawdown_pct', 15)
    
    return drawdown < max_drawdown, drawdown

def check_position_size(portfolio, position_size_pct, risk_params):
    """Check if position size is within limits"""
    max_position = risk_params.get('max_position_pct', 100)
    return position_size_pct <= max_position

# Signal generation
def generate_signals(worldview, portfolio):
    """Generate trade signals from active theses"""
    signals = []
    risk_params = worldview.get('risk_params', {})
    confidence_threshold = risk_params.get('confidence_threshold_for_trade', 0.65)
    
    # Check drawdown first
    within_drawdown, current_dd = check_drawdown(portfolio, risk_params)
    if not within_drawdown:
        print(f"[-] Drawdown limit reached ({current_dd:.1f}%), no new signals")
        return signals
    
    for thesis in worldview.get('active_theses', []):
        # Only generate signals for watching theses above confidence threshold
        if thesis.get('status') != 'watching':
            continue
        if thesis.get('confidence', 0) < confidence_threshold:
            continue
        
        asset = thesis.get('asset')
        direction = thesis.get('direction', 'neutral')
        
        if not asset or direction == 'neutral':
            continue
        
        # Check if we already have a position
        existing_position = None
        for pos in portfolio.get('positions', []):
            if pos.get('asset') == asset:
                existing_position = pos
                break
        
        if existing_position:
            continue  # Skip if already positioned
        
        # Determine position size based on confidence
        confidence = thesis.get('confidence', 0.5)
        base_size_pct = 20  # Base position size
        size_pct = base_size_pct * confidence  # Scale by confidence
        size_pct = min(size_pct, risk_params.get('max_position_pct', 100))
        
        signal = {
            'signal_id': f"sig_{hashlib.md5(f'{asset}_{datetime.now().isoformat()}'.encode()).hexdigest()[:8]}",
            'thesis_id': thesis.get('id'),
            'asset': asset,
            'direction': direction,
            'action': 'BUY' if direction == 'long' else 'SELL',
            'size_pct': round(size_pct, 1),
            'confidence': confidence,
            'rationale': thesis.get('thesis', ''),
            'sources': thesis.get('sources', []),
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'status': 'pending'
        }
        
        signals.append(signal)
    
    return signals

# Asset mapping for ACP execution
def map_asset_to_acp(asset):
    """Map trading asset to ACP-compatible asset"""
    # Crypto mappings
    crypto_map = {
        'BTC': 'WBTC',  # Wrapped BTC on Base
        'ETH': 'WETH',
        'SOL': None,  # Not available on Base
        'AVAX': None,
        'LINK': 'LINK',
        'UNI': 'UNI',
        'AAVE': 'AAVE',
    }
    
    # For non-crypto, we need proxy assets
    # These are synthetic or related crypto assets
    equity_proxy_map = {
        'SNAP': 'WETH',  # Proxy: use ETH as general risk-on proxy
        'META': 'WETH',
        'GOOGL': 'WETH',
        'MSFT': 'WETH',
        'AAPL': 'WETH',
        'NVDA': 'WETH',
    }
    
    # Try direct crypto mapping first
    if asset in crypto_map:
        return crypto_map[asset], 'direct', asset
    
    # Try equity proxy
    if asset in equity_proxy_map:
        return equity_proxy_map[asset], 'proxy', asset
    
    # Default to WETH as general risk proxy
    return 'WETH', 'proxy', asset

def execute_signal(signal, portfolio, worldview):
    """Execute a trade signal via ACP"""
    asset = signal.get('asset')
    direction = signal.get('direction')
    size_pct = signal.get('size_pct', 10)
    
    # Map to ACP asset
    acp_asset, mapping_type, original_asset = map_asset_to_acp(asset)
    
    if acp_asset is None:
        print(f"[-] Cannot execute {asset}: no ACP mapping available")
        return None
    
    # Calculate trade size
    portfolio_value = portfolio.get('total_value_usd', 0)
    trade_value = portfolio_value * (size_pct / 100)
    
    # Create trade record
    trade = {
        'trade_id': f"trade_{hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:8]}",
        'signal_id': signal.get('signal_id'),
        'thesis_id': signal.get('thesis_id'),
        'original_asset': original_asset,
        'executed_asset': acp_asset,
        'mapping_type': mapping_type,
        'action': signal.get('action'),
        'direction': direction,
        'size_pct': size_pct,
        'trade_value_usd': round(trade_value, 2),
        'entry_price': None,  # Will be filled by actual execution
        'status': 'pending_execution',
        'acp_agent': 'ethy-ai',
        'acp_wallet': ACP_WALLET,
        'rationale': signal.get('rationale'),
        'sources': signal.get('sources'),
        'generated_at': signal.get('generated_at'),
        'executed_at': None,
        'tx_hash': None
    }
    
    # Mark thesis as trading
    for thesis in worldview.get('active_theses', []):
        if thesis.get('id') == signal.get('thesis_id'):
            thesis['status'] = 'trading'
            thesis['trade_id'] = trade['trade_id']
            break
    
    print(f"[+] Trade generated: {trade['action']} {acp_asset} ({mapping_type} for {original_asset})")
    print(f"    Size: ${trade['trade_value_usd']:.2f} ({size_pct}%)")
    print(f"    Agent: {trade['acp_agent']}")
    
    return trade

def save_pending_signals(signals):
    with open(SIGNALS_FILE, 'w') as f:
        json.dump(signals, f, indent=2)

# Main execution loop
def run_executor():
    print(f"\n{'='*60}")
    print(f"ENTROPY SURVIVOR - TRADE EXECUTION")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")
    
    worldview = load_worldview()
    portfolio = load_portfolio()
    
    print(f"[*] Portfolio value: ${portfolio['total_value_usd']:.2f}")
    print(f"[*] Active theses: {len(worldview.get('active_theses', []))}")
    print(f"[*] Open positions: {len(portfolio.get('positions', []))}")
    
    # Check drawdown
    risk_params = worldview.get('risk_params', {})
    within_dd, current_dd = check_drawdown(portfolio, risk_params)
    print(f"[*] Current drawdown: {current_dd:.1f}% (limit: {risk_params.get('max_drawdown_pct', 15)}%)")
    
    # Generate signals
    print(f"\n[*] Generating trade signals...")
    signals = generate_signals(worldview, portfolio)
    print(f"[*] Signals generated: {len(signals)}")
    
    # Execute signals
    trades_executed = []
    for signal in signals:
        print(f"\n[*] Processing signal: {signal['signal_id']}")
        trade = execute_signal(signal, portfolio, worldview)
        if trade:
            save_trade(trade)
            trades_executed.append(trade)
    
    # Update worldview with trading status
    with open(WORLDVIEW_FILE, 'w') as f:
        json.dump(worldview, f, indent=2)
    
    # Save pending signals for manual review if needed
    save_pending_signals(signals)
    
    print(f"\n{'='*60}")
    print(f"EXECUTION COMPLETE")
    print(f"Trades generated: {len(trades_executed)}")
    print(f"{'='*60}\n")
    
    return trades_executed

if __name__ == "__main__":
    run_executor()
