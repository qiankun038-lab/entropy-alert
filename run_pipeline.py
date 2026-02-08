#!/usr/bin/env python3
"""
ENTROPY SURVIVOR - Main Pipeline Orchestrator
Runs the complete: Ingest → Synthesize → Execute pipeline
"""

import sys
import os
from pathlib import Path

# Add paths
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from ingestion.ingest import run_ingestion
from worldview.synthesize import run_synthesis
from execution.executor import run_executor

def run_pipeline(execute_trades=True):
    """Run the full pipeline"""
    print("\n" + "="*70)
    print("  ENTROPY SURVIVOR - ALPHA INTELLIGENCE SYSTEM")
    print("  Running full pipeline: INGEST → SYNTHESIZE → EXECUTE")
    print("="*70 + "\n")
    
    # Step 1: Ingest
    try:
        new_alphas = run_ingestion()
        print(f"\n✓ Ingestion complete: {new_alphas} new alphas\n")
    except Exception as e:
        print(f"\n✗ Ingestion failed: {e}\n")
        new_alphas = 0
    
    # Step 2: Synthesize
    try:
        worldview = run_synthesis()
        print(f"\n✓ Synthesis complete\n")
    except Exception as e:
        print(f"\n✗ Synthesis failed: {e}\n")
        worldview = None
    
    # Step 3: Execute (if enabled)
    if execute_trades:
        try:
            trades = run_executor()
            print(f"\n✓ Execution complete: {len(trades)} trades generated\n")
        except Exception as e:
            print(f"\n✗ Execution failed: {e}\n")
            trades = []
    else:
        print("\n⊘ Trade execution skipped\n")
        trades = []
    
    print("="*70)
    print("  PIPELINE COMPLETE")
    print("="*70 + "\n")
    
    return {
        'new_alphas': new_alphas,
        'worldview': worldview,
        'trades': trades
    }

if __name__ == "__main__":
    # Parse args
    execute = '--no-execute' not in sys.argv
    run_pipeline(execute_trades=execute)
