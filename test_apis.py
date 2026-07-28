"""快速测试 FRED + FedWatch API"""
import sys, os
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv; load_dotenv()
from fed_data import FedDataFetcher

print("="*60)
print("  FedSight AI - FRED + FedWatch API Test")
print("="*60)

fetcher = FedDataFetcher()
macro, fw = fetcher.get_full_snapshot()

print(f"\n{'='*60}")
print("  REAL-TIME MACRO SNAPSHOT (as of July 2026)")
print(f"{'='*60}")
print(f"\n  [Inflation] PCE YoY: {macro.pce_yoy}% | Core PCE: {macro.core_pce_yoy}% | CPI: {macro.cpi_yoy}%")
print(f"  [Labor]     Unemployment: {macro.unemployment_rate}% | JOLTS: {macro.jolts_openings}")
print(f"  [Rates]     Fed Rate: {macro.fed_funds_rate}% | 3m: {macro.treasury_3m}% | 2y: {macro.treasury_2y}% | 10y: {macro.treasury_10y}%")
print(f"  [Spread]    2s10s: {macro.yield_curve_2s10s} | real rate(3m-corePCE): {macro.real_rate_3m}%")
print(f"  [Economy]   ISM Mfg: {macro.ism_manufacturing}")
print(f"  [Risk]      VIX: {macro.vix}")
print(f"\n  [FedWatch]  Implied rate: {fw.implied_rate}% | Action: {fw.implied_action}")
print(f"  [FedWatch]  {fw.market_sentiment}")

print(f"\n{'='*60}")
print("  SUCCESS: FRED + FedWatch APIs working!")
print(f"{'='*60}")
