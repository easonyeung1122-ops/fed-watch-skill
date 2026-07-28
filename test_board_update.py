"""测试 Board Members 自动更新"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

print("="*60)
print("  Testing Board Members Auto-Update")
print("="*60)
print()

# Test 1: fetch_board module
print("--- Test 1: fetch_board.py ---")
from fetch_board import fetch_board_members
members = fetch_board_members()
print(f"\n  Found {len(members)} members\n")

# Test 2: fed_sim integration
print("--- Test 2: fed_sim.py integration ---")
from fed_sim import FOMC_MEMBERS
print(f"\n  FOMC_MEMBERS loaded: {len(FOMC_MEMBERS)} members\n")
for i, m in enumerate(FOMC_MEMBERS, 1):
    print(f"  {i}. {m['name']:25s} | {m['role']:25s} | {m['archetype']}")

print(f"\n{'='*60}")
print("  Auto-update working!")
print("="*60)
