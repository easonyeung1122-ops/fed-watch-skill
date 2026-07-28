"""测试多种方式获取联邦基金利率预期"""
import sys, os
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
import requests

print("=== 方案1: yfinance 联邦基金期货 ===\n")

# CME Fed Funds 期货
tickers = ["ZQ=F", "ZN=F", "ZF=F", "ZT=F"]
for t in tickers:
    try:
        ticker = yf.Ticker(t)
        hist = ticker.history(period="5d")
        info = ticker.info
        if not hist.empty:
            last = hist['Close'].iloc[-1]
            print(f"{t}: Price={last:.4f}")
        else:
            print(f"{t}: No history")
    except Exception as e:
        print(f"{t}: Error - {e}")

print("\n=== 方案2: FRED 期货隐含利率 ===\n")

try:
    # FRED FF = Federal Funds Rate (implied by futures)
    from dotenv import load_dotenv; load_dotenv()
    fred_key = os.getenv("FRED_API_KEY")
    
    for series in ["FF", "DFF", "FEDFUNDS"]:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series,
            "api_key": fred_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 5,
        }
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        obs = data.get("observations", [])
        if obs:
            vals = [(o["date"], o["value"]) for o in obs if o["value"] != "."]
            print(f"\n{series}:")
            for d, v in vals[:3]:
                print(f"  {d}: {v}")
        else:
            print(f"{series}: No data")
except Exception as e:
    print(f"Error: {e}")

print("\n=== 方案3: 腾讯/新浪财经API ===\n")

try:
    # 美元利率
    url = "https://api-ddc-wscn.awtmt.com/market/real?fields=prod_name,last_px,px_change,px_change_rate&prod_code=USINTR.US"
    resp = requests.get(url, timeout=10)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(str(data)[:500])
except Exception as e:
    print(f"Error: {e}")
