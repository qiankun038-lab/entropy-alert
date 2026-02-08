# Entropy Survivor - Alpha Intelligence System

An autonomous trading system that ingests alpha from multiple sources, synthesizes a living worldview, and executes trades via ACP.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     ENTROPYSURVIVOR.COM                      │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│                       DATA LAYER                             │
│  alpha.jsonl | worldview.json | trades.jsonl | portfolio.json│
└──────────────────────────────────────────────────────────────┘
       │                  │                    │
   ┌───┴───┐         ┌────┴────┐         ┌────┴────┐
   │INGEST │    →    │SYNTHESIZE│    →   │EXECUTE  │
   └───────┘         └──────────┘         └─────────┘
```

## Quick Start

```bash
# Run full pipeline (ingest → synthesize → execute)
python run_pipeline.py

# Run without trade execution
python run_pipeline.py --no-execute

# Start web server
python server.py

# Run individual components
python ingestion/ingest.py
python worldview/synthesize.py
python execution/executor.py
```

## Alpha Sources

### Twitter (via Nitter RSS)
- @Citrini7
- @QwQiao
- @tbr90
- @izebel_eth

### Substack (RSS)
- Citrini
- Chamath
- CryptoNarratives
- evanss6
- OldCoinBad

### Telegram
- AnteaterAmazon
- TradeWithChop

### Websites
- epilepsywarning.com

## Data Files

| File | Description |
|------|-------------|
| `data/alpha.jsonl` | Raw alpha signals from all sources |
| `data/worldview.json` | Current worldview state |
| `data/trades.jsonl` | Trade execution log |
| `data/portfolio.json` | Portfolio state and P&L |
| `data/source_weights.json` | Source trust scores |
| `logs/state_history.jsonl` | Historical worldview states |

## Risk Parameters

- **Max Drawdown**: 15%
- **Max Position Size**: 100%
- **Confidence Threshold**: 65%

## Website Views

| Route | Description |
|-------|-------------|
| `/` | Alpha feed - live incoming signals |
| `#worldview` | Current beliefs, theses, sector views |
| `#portfolio` | Positions, P&L tracking |
| `#execution` | Trade queue and execution logs |
| `#reflection` | Performance attribution, source trust |
| `#input` | Human override interface |

## ACP Integration

Trades are executed via the ACP wallet:
- **Address**: `0x19259e95855cD1f167ebBbe2836Bc62ac3B99c1B`
- **Network**: Base
- **Agent**: Ethy AI

Non-crypto assets use proxy mapping (e.g., SNAP → WETH as risk-on proxy).

## Cron Schedule

Recommended: Run pipeline hourly
```
0 * * * * cd /path/to/entropy-survivor && python run_pipeline.py
```

---

Built by Entropy Survivor for autonomous alpha generation and execution.
