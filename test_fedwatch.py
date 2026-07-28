"""测试 CME FedWatch API 原始返回格式"""
import sys, os
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests, json

url = "https://www.cmegroup.com/CmeWS/mvc/UsdFls/UserDistibutionDelegator/getUserDistributionData/435/426/false"
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
data = resp.json()

print(f"Type: {type(data)}")
print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
print(f"Length: {len(data) if isinstance(data, list) else 'N/A'}")

if isinstance(data, list) and len(data) > 0:
    print(f"\nFirst element type: {type(data[0])}")
    print(f"First element: {data[0]}")
elif isinstance(data, dict):
    # Pretty print first level
    for k, v in data.items():
        val_str = str(v)[:200]
        print(f"\n{k}: {val_str}")
    # Check for nested data
    for k, v in data.items():
        if isinstance(v, list) and len(v) > 0:
            print(f"\n--- {k}[0] ---")
            print(json.dumps(v[0], indent=2, ensure_ascii=False)[:500])
        elif isinstance(v, dict):
            print(f"\n--- {k} (dict) ---")
            print(json.dumps(v, indent=2, ensure_ascii=False)[:500])
