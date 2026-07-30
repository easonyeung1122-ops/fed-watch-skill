"""
FedSight AI - 实时数据管道
Primary: Bloomberg Terminal (blpapi) → 14项宏观指标 + FF Futures
Fallback: FRED API + yfinance + CME FedWatch
"""
import os, sys, json, re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from dotenv import load_dotenv

try:
    import blpapi
    HAS_BLOOMBERG = True
except ImportError:
    HAS_BLOOMBERG = False

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

# ═══════════════════════════════════════════════════════════
# Bloomberg Ticker → Macro Field Mapping (Primary Source)
# ═══════════════════════════════════════════════════════════

BBG_MACRO_MAP = {
    # (ticker, field, field_name, is_yoy)
    # Primary tickers first, fallbacks in comments
    "core_pce_yoy":             ("PCE CYOY Index",     "PX_LAST", "Core PCE YoY", True),
    "pce_yoy":                  ("PCE DEFY Index",     "PX_LAST", "PCE YoY", True),        # alt: PCE CHNG Index
    "cpi_yoy":                  ("CPI YOY Index",       "PX_LAST", "CPI YoY", True),
    "unemployment_rate":        ("USURTOT Index",       "PX_LAST", "Unemployment Rate", False),
    "nonfarm_payrolls":         ("NFP TCH Index",       "PX_LAST", "Nonfarm Payrolls (MoM Chg)", False),
    "treasury_3m":              ("USGG3M Index",        "PX_LAST", "3M Treasury Yield", False),
    "treasury_2y":              ("USGG2YR Index",       "PX_LAST", "2Y Treasury Yield", False),
    "treasury_10y":             ("USGG10YR Index",      "PX_LAST", "10Y Treasury Yield", False),
    "vix":                      ("VIX Index",           "PX_LAST", "VIX", False),
    "fed_funds_rate":           ("FDTR Index",          "PX_LAST", "Fed Funds Target (Upper)", False),
    "gdp_real":                 ("GDP CQOQ Index",      "PX_LAST", "GDP QoQ Annualized", False),
    "jolts_openings":           ("JOLTTOTL Index",      "PX_LAST", "JOLTS Job Openings (Total)", False),
    "ism_manufacturing":        ("NAPMPMI Index",       "PX_LAST", "ISM Manufacturing PMI", False),
    "avg_hourly_earnings_yoy":  ("AHE YOY Index",       "PX_LAST", "Avg Hourly Earnings YoY", True),
}

# BBG Fed Funds Futures (FedWatch equivalent)
BBG_FEDWATCH_MAP = {
    "ff_current_month":  ("FFA Comdty",    "PX_LAST", "FF Futures Current Month"),
    "ff_next_month":     ("FFB Comdty",    "PX_LAST", "FF Futures Next Month"),
    "ff_3month":         ("FFC Comdty",    "PX_LAST", "FF Futures 3rd Month"),
    "fed_effective":     ("FEDL01 Index",  "PX_LAST", "Effective Fed Funds Rate"),
    "sofr_rate":         ("SOFRRATE Index","PX_LAST", "SOFR Rate"),
}

# ═══════════════════════════════════════════════════════════
# FRED Fallback Mappings (unchanged)
# ═══════════════════════════════════════════════════════════

FRED_SERIES = {
    "core_pce_yoy":             "PCEPILFE",
    "pce_yoy":                  "PCEPI",
    "cpi_yoy":                  "CPIAUCSL",
    "unemployment_rate":        "UNRATE",
    "nonfarm_payrolls":         "PAYEMS",
    "treasury_3m":              "DTB3",
    "treasury_2y":              "DGS2",
    "treasury_10y":             "DGS10",
    "vix":                      "VIXCLS",
    "fed_funds_rate":           "DFEDTARU",
    "gdp_real":                 "GDPC1",
    "jolts_openings":           "JTSJOL",
    "ism_manufacturing":        "NAPM",
    "avg_hourly_earnings_yoy":  "CES0500000003",
}


@dataclass
class MacroSnapshot:
    """单次FOMC会议前的宏观数据快照"""
    meeting_date: str
    pce_yoy: Optional[float] = None
    core_pce_yoy: Optional[float] = None
    cpi_yoy: Optional[float] = None
    unemployment_rate: Optional[float] = None
    nonfarm_payrolls: Optional[float] = None
    treasury_3m: Optional[float] = None
    treasury_2y: Optional[float] = None
    treasury_10y: Optional[float] = None
    vix: Optional[float] = None
    fed_funds_rate: Optional[float] = None
    gdp_real: Optional[float] = None
    jolts_openings: Optional[float] = None
    avg_hourly_earnings_yoy: Optional[float] = None
    ism_manufacturing: Optional[float] = None
    # Derived
    yield_curve_2s10s: Optional[float] = None
    yield_curve_3m10y: Optional[float] = None
    real_rate_3m: Optional[float] = None
    # Data source tag
    data_source: str = "unknown"

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "meeting_date": self.meeting_date,
            "pce_index_yoy": self.pce_yoy or 0,
            "cpi_index_yoy": self.cpi_yoy or 0,
            "core_pce_yoy": self.core_pce_yoy or 0,
            "inflation_expectations_1yr": None,
            "treasury_yield_3m": self.treasury_3m or 0,
            "treasury_yield_6m": None,
            "m2_supply_level_sa": None,
            "bbk_real_gdp_nowcast": self.gdp_real or 0,
            "unemployment_rate_u3": self.unemployment_rate or 0,
            "vix_index": self.vix or 0,
            "fed_chair": "Powell",
            "white_house_party": "Republican",
            "previous_fftr_target": int((self.fed_funds_rate or 0) * 100),
            "previous_change": 0,
        }])


@dataclass
class FedWatchSnapshot:
    """CME FedWatch 利率预期数据"""
    meeting_date: str
    probabilities: Dict[str, float] = field(default_factory=dict)
    implied_rate: Optional[float] = None
    implied_action: str = ""
    market_sentiment: str = ""


# ═══════════════════════════════════════════════════════════
# Bloomberg Data Fetcher (Primary)
# ═══════════════════════════════════════════════════════════

class BloombergFetcher:
    """Bloomberg Terminal 数据获取器"""

    def __init__(self):
        self.available = HAS_BLOOMBERG
        if not self.available:
            print("[Bloomberg] blpapi not installed, Bloomberg unavailable")

    @staticmethod
    def _send_bdp_request(securities: List[str], fields: List[str]) -> dict:
        """发送Bloomberg BDP (Reference Data) 请求，返回 {ticker: {field: value}}"""
        session = blpapi.Session()
        if not session.start():
            raise ConnectionError("Failed to start Bloomberg session")
        if not session.openService("//blp/refdata"):
            raise ConnectionError("Failed to open refdata service")

        service = session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        for sec in securities:
            request.append("securities", sec)
        for f in fields:
            request.append("fields", f)

        session.sendRequest(request)

        results = {}
        while True:
            ev = session.nextEvent(500)
            if ev.eventType() == blpapi.Event.RESPONSE:
                for msg in ev:
                    sec_data = msg.getElement("securityData")
                    for i in range(sec_data.numValues()):
                        sec_elem = sec_data.getValueAsElement(i)
                        ticker = sec_elem.getElementAsString("security")
                        field_data = sec_elem.getElement("fieldData")
                        results[ticker] = {}
                        for j in range(field_data.numElements()):
                            fd = field_data.getElement(j)
                            try:
                                results[ticker][str(fd.name())] = fd.getValueAsFloat()
                            except:
                                try:
                                    results[ticker][str(fd.name())] = fd.getValueAsString()
                                except:
                                    pass
                break

        session.stop()
        return results

    @staticmethod
    def _send_bdp_batched(securities: List[str], fields: List[str], batch_size: int = 8) -> dict:
        """Split into smaller batches to avoid Bloomberg data limits"""
        all_results = {}
        for i in range(0, len(securities), batch_size):
            batch = securities[i:i+batch_size]
            try:
                batch_results = BloombergFetcher._send_bdp_request(batch, fields)
                all_results.update(batch_results)
            except Exception as e:
                print(f"  [Bloomberg] Batch {i//batch_size} failed: {e}")
        return all_results

    def fetch_macro(self) -> Dict[str, float]:
        """从 Bloomberg 获取所有宏观指标的当前值"""
        print("\n[Bloomberg] Fetching macro data via BDP (batched)...")

        # Build ticker list (deduplicated)
        ticker_set = set()
        ticker_list = []
        for field_name, (ticker, bbg_field, desc, _) in BBG_MACRO_MAP.items():
            if ticker not in ticker_set:
                ticker_set.add(ticker)
                ticker_list.append(ticker)

        try:
            raw = self._send_bdp_batched(ticker_list, ["PX_LAST"], batch_size=8)
        except Exception as e:
            print(f"  [Bloomberg] BDP request failed: {e}")
            return {}

        # Map back to our field names
        results = {}
        for field_name, (ticker, bbg_field, desc, _) in BBG_MACRO_MAP.items():
            if ticker in raw and bbg_field in raw[ticker]:
                val = raw[ticker][bbg_field]
                if isinstance(val, str) and val.upper() in ("N.A.", "#N/A", "NAN"):
                    print(f"  -- {desc} ({ticker}): N/A")
                    continue
                results[field_name] = float(val)
                print(f"  OK {desc} ({ticker}): {val}")
            else:
                print(f"  -- {desc} ({ticker}): No data")

        return results

    def fetch_fedwatch(self) -> Dict[str, float]:
        """从 Bloomberg 获取联邦基金期货隐含利率"""
        print("\n[Bloomberg] Fetching Fed Funds futures data...")

        ticker_list = []
        for name, (ticker, bbg_field, desc) in BBG_FEDWATCH_MAP.items():
            ticker_list.append(ticker)

        try:
            raw = self._send_bdp_batched(ticker_list, ["PX_LAST"], batch_size=8)
        except Exception as e:
            print(f"  [Bloomberg] FF futures request failed: {e}")
            return {}

        results = {}
        for name, (ticker, bbg_field, desc) in BBG_FEDWATCH_MAP.items():
            if ticker in raw and bbg_field in raw[ticker]:
                val = float(raw[ticker][bbg_field])
                results[name] = val
                if name.startswith("ff_"):
                    implied = 100.0 - val
                    print(f"  OK {desc} ({ticker}): Price={val:.4f}, Implied Rate={implied:.4f}%")
                else:
                    print(f"  OK {desc} ({ticker}): {val}")
            else:
                print(f"  -- {desc} ({ticker}): No data")

        return results


# ═══════════════════════════════════════════════════════════
# Main Data Fetcher (Bloomberg → FRED → yfinance)
# ═══════════════════════════════════════════════════════════

class FedDataFetcher:
    """主数据获取器：Bloomberg (Primary) → FRED → yfinance"""

    def __init__(self, fred_api_key: Optional[str] = None):
        self.fred_key = fred_api_key or os.getenv("FRED_API_KEY", "")
        self.fred_base = "https://api.stlouisfed.org/fred"
        self.bbg = BloombergFetcher() if HAS_BLOOMBERG else None
        self._source: str = "unknown"

    @property
    def data_source(self) -> str:
        return self._source

    # ─── FRED Fallback Methods ──────────────────────────

    def fetch_fred_series(self, series_id: str, lookback_months: int = 6) -> pd.Series:
        url = f"{self.fred_base}/series/observations"
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=lookback_months * 32)).strftime("%Y-%m-%d")
        params = {
            "series_id": series_id, "api_key": self.fred_key,
            "file_type": "json", "observation_start": start_date,
            "observation_end": end_date, "sort_order": "desc",
        }
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            values, dates = [], []
            for obs in data.get("observations", []):
                if obs["value"] != ".":
                    values.append(float(obs["value"]))
                    dates.append(obs["date"])
            series = pd.Series(values, index=pd.to_datetime(dates))
            series.sort_index(ascending=False, inplace=True)
            return series
        except Exception as e:
            print(f"  [FRED WARN] {series_id}: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def calc_yoy(series: pd.Series, months_back: int = 12) -> pd.Series:
        if len(series) < months_back:
            return pd.Series(dtype=float)
        yoy = pd.Series(dtype=float)
        for idx in series.index:
            ref_date = idx - pd.DateOffset(months=months_back)
            before = series[series.index <= ref_date]
            if not before.empty:
                old_val = before.iloc[-1]
                new_val = series.loc[idx]
                if old_val and old_val != 0:
                    yoy.loc[idx] = (new_val / old_val - 1) * 100
        yoy.sort_index(ascending=False, inplace=True)
        return yoy

    YOY_SERIES = {"pce_yoy", "core_pce_yoy", "cpi_yoy", "nonfarm_payrolls", "avg_hourly_earnings_yoy"}

    # ─── Main: Build Macro Snapshot ─────────────────────

    def fetch_all_macro(self, as_of_date: Optional[str] = None) -> Dict[str, pd.Series]:
        """
        获取宏观数据：Bloomberg → FRED fallback
        Returns: {field_name: pd.Series}
        """
        results = {}

        # ─── Try Bloomberg first ───
        if self.bbg and self.bbg.available:
            print("\n[Data] Primary source: Bloomberg Terminal")
            bbg_data = self.bbg.fetch_macro()
            if bbg_data:
                self._source = "bloomberg"
                for field_name, value in bbg_data.items():
                    series = pd.Series([value], index=[pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))])
                    results[field_name] = series
                return results
            else:
                print("  [Data] Bloomberg returned no data, trying FRED...")

        # ─── Fallback: FRED ───
        if self.fred_key and self.fred_key not in ("your_fred_api_key_here", ""):
            print("\n[Data] Source: FRED API")
            self._source = "fred"
            for field_name, series_id in FRED_SERIES.items():
                try:
                    lookback = 14 if field_name in self.YOY_SERIES else 6
                    series = self.fetch_fred_series(series_id, lookback_months=lookback)
                    if not series.empty:
                        if field_name in self.YOY_SERIES:
                            yoy = self.calc_yoy(series, months_back=12)
                            if not yoy.empty:
                                results[field_name] = yoy
                                print(f"  OK {series_id}: {yoy.iloc[0]:.2f}% (YoY)")
                        else:
                            results[field_name] = series
                            print(f"  OK {series_id}: {series.iloc[0]:.2f}")
                    else:
                        print(f"  -- {series_id}: No data")
                except Exception as e:
                    print(f"  ERR {series_id}: {e}")
        else:
            print("\n[Data] No Bloomberg and no FRED key. Macro data unavailable.")
            self._source = "none"

        return results

    def build_macro_snapshot(
        self, meeting_date: str, data_cache: Optional[Dict[str, pd.Series]] = None
    ) -> MacroSnapshot:
        if data_cache is None:
            data_cache = self.fetch_all_macro()

        def get_latest(series: pd.Series, ref_date: str) -> Optional[float]:
            cutoff = pd.to_datetime(ref_date)
            valid = series[series.index <= cutoff]
            return float(valid.iloc[0]) if not valid.empty else None

        snap = MacroSnapshot(meeting_date=meeting_date, data_source=self._source)

        field_map = {
            "pce_yoy": "pce_yoy", "core_pce_yoy": "core_pce_yoy",
            "cpi_yoy": "cpi_yoy", "unemployment_rate": "unemployment_rate",
            "nonfarm_payrolls": "nonfarm_payrolls", "treasury_3m": "treasury_3m",
            "treasury_2y": "treasury_2y", "treasury_10y": "treasury_10y",
            "vix": "vix", "fed_funds_rate": "fed_funds_rate",
            "gdp_real": "gdp_real", "jolts_openings": "jolts_openings",
            "avg_hourly_earnings_yoy": "avg_hourly_earnings_yoy",
            "ism_manufacturing": "ism_manufacturing",
        }

        for key, attr in field_map.items():
            if key in data_cache:
                val = get_latest(data_cache[key], meeting_date)
                setattr(snap, attr, val)

        if snap.treasury_2y and snap.treasury_10y:
            snap.yield_curve_2s10s = snap.treasury_10y - snap.treasury_2y
        if snap.treasury_3m and snap.treasury_10y:
            snap.yield_curve_3m10y = snap.treasury_10y - snap.treasury_3m
        if snap.treasury_3m and snap.core_pce_yoy:
            snap.real_rate_3m = snap.treasury_3m - snap.core_pce_yoy

        return snap

    # ─── FedWatch / Market Expectations ──────────────────

    def fetch_fedwatch(self) -> FedWatchSnapshot:
        """获取利率预期：Bloomberg FF Futures → yfinance ZQ=F"""
        print("\n[FedWatch] Fetching rate expectations...")
        snapshot = FedWatchSnapshot(meeting_date=datetime.now().strftime("%Y-%m-%d"))

        # ─── Bloomberg FF Futures (Primary) ───
        if self.bbg and self.bbg.available:
            ff_data = self.bbg.fetch_fedwatch()
            if ff_data:
                # Current month FF futures → implied rate
                current_month_price = ff_data.get("ff_current_month")
                fed_effective = ff_data.get("fed_effective")
                sofr = ff_data.get("sofr_rate")

                if current_month_price:
                    implied = 100.0 - current_month_price
                    snapshot.implied_rate = implied
                    snapshot.probabilities["BBG_FF1_implied"] = implied

                if fed_effective:
                    snapshot.probabilities["BBG_FEDL01"] = fed_effective

                if sofr:
                    snapshot.probabilities["BBG_SOFR"] = sofr

                # Determine market action
                if snapshot.implied_rate and fed_effective:
                    diff = snapshot.implied_rate - fed_effective
                    if diff > 0.15:
                        snapshot.implied_action = "HIKE"
                        snapshot.market_sentiment = (
                            f"[Bloomberg] Market expects ~{abs(diff):.0f}bp HIKE "
                            f"(FF1 implied: {snapshot.implied_rate:.2f}%, "
                            f"Effective: {fed_effective:.2f}%)"
                        )
                    elif diff < -0.15:
                        snapshot.implied_action = "CUT"
                        snapshot.market_sentiment = (
                            f"[Bloomberg] Market expects ~{abs(diff):.0f}bp CUT "
                            f"(FF1 implied: {snapshot.implied_rate:.2f}%, "
                            f"Effective: {fed_effective:.2f}%)"
                        )
                    else:
                        snapshot.implied_action = "HOLD"
                        snapshot.market_sentiment = (
                            f"[Bloomberg] Market expects HOLD "
                            f"(FF1 implied: {snapshot.implied_rate:.2f}%, "
                            f"Effective: {fed_effective:.2f}%)"
                        )
                elif snapshot.implied_rate:
                    snapshot.market_sentiment = f"[Bloomberg] FF1 implied rate: {snapshot.implied_rate:.2f}%"

                print(f"  Action: {snapshot.implied_action} | {snapshot.market_sentiment}")
                return snapshot

        # ─── Fallback: yfinance ZQ=F ───
        if HAS_YFINANCE:
            print("  [FedWatch] Bloomberg unavailable, trying yfinance ZQ=F...")
            try:
                zq = yf.Ticker("ZQ=F")
                hist = zq.history(period="5d")
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                    implied = 100 - price
                    snapshot.implied_rate = implied
                    snapshot.market_sentiment = f"[yfinance] ZQ=F implied: {implied:.2f}%"
                    print(f"  OK ZQ=F: Price={price:.2f}, Implied={implied:.2f}%")
            except Exception as e:
                print(f"  -- yfinance ZQ=F: {e}")

        return snapshot

    # ─── Full Snapshot ────────────────────────────────────

    def get_full_snapshot(
        self, meeting_date: Optional[str] = None
    ) -> Tuple[MacroSnapshot, FedWatchSnapshot]:
        if meeting_date is None:
            meeting_date = datetime.now().strftime("%Y-%m-%d")

        print(f"\n{'='*60}")
        print(f"  FedSight AI - Real-Time Data Pipeline")
        print(f"  Date: {meeting_date}")
        print(f"  Source Priority: Bloomberg > FRED > yfinance")
        print(f"{'='*60}")

        macro_data = self.fetch_all_macro(as_of_date=meeting_date)
        macro = self.build_macro_snapshot(meeting_date, macro_data)
        fedwatch = self.fetch_fedwatch()

        return macro, fedwatch


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    fetcher = FedDataFetcher()
    macro, fw = fetcher.get_full_snapshot()

    print(f"\n{'='*60}")
    print(f"  Macro Data Summary (Source: {macro.data_source})")
    print(f"{'='*60}")
    print(f"\n  [Inflation]")
    print(f"    Core PCE YoY:  {macro.core_pce_yoy or 'N/A'}%")
    print(f"    PCE YoY:       {macro.pce_yoy or 'N/A'}%")
    print(f"    CPI YoY:       {macro.cpi_yoy or 'N/A'}%")
    print(f"\n  [Labor Market]")
    print(f"    Unemployment:  {macro.unemployment_rate or 'N/A'}%")
    print(f"    NFP (MoM):     {macro.nonfarm_payrolls or 'N/A'}K")
    print(f"    JOLTS:         {macro.jolts_openings or 'N/A'}M")
    print(f"    Avg Hrly Earn: {macro.avg_hourly_earnings_yoy or 'N/A'}% YoY")
    print(f"\n  [Rates & Financial Conditions]")
    print(f"    Fed Funds:     {macro.fed_funds_rate or 'N/A'}%")
    print(f"    3M Treasury:   {macro.treasury_3m or 'N/A'}%")
    print(f"    2Y Treasury:   {macro.treasury_2y or 'N/A'}%")
    print(f"    10Y Treasury:  {macro.treasury_10y or 'N/A'}%")
    print(f"    2s10s Spread:  {macro.yield_curve_2s10s or 'N/A'} bps")
    print(f"    Real Rate:     {macro.real_rate_3m or 'N/A'}%")
    print(f"\n  [Real Economy]")
    print(f"    GDP Real:      {macro.gdp_real or 'N/A'}%")
    print(f"    ISM Mfg PMI:   {macro.ism_manufacturing or 'N/A'}")
    print(f"\n  [Risk]")
    print(f"    VIX:           {macro.vix or 'N/A'}")
    print(f"\n  [Fed Funds Futures]")
    print(f"    Implied Rate:  {fw.implied_rate or 'N/A':.2f}%" if fw.implied_rate else "    Implied Rate:  N/A")
    print(f"    Market View:   {fw.market_sentiment}")
