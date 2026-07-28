"""
FedSight AI - 实时数据管道
从 FRED API 获取宏观指标 + 从 CME FedWatch 获取市场利率预期
"""
import os
import sys
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from dotenv import load_dotenv

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

# Windows UTF-8 support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

# ─── FRED 数据映射：宏观指标 → FRED Series ID ───
FRED_SERIES = {
    "pce_index_yoy": "PCEPI",           # PCE物价指数同比
    "cpi_index_yoy": "CPIAUCSL",        # CPI同比
    "core_pce_yoy": "PCEPILFE",         # 核心PCE同比（Fed最关注）
    "unemployment_rate_u3": "UNRATE",   # U3失业率
    "nonfarm_payrolls": "PAYEMS",       # 非农就业
    "treasury_yield_3m": "DTB3",        # 3个月国债收益率
    "treasury_yield_2y": "DGS2",        # 2年期国债收益率
    "treasury_yield_10y": "DGS10",      # 10年期国债收益率
    "vix_index": "VIXCLS",              # VIX波动率指数
    "m2_supply": "M2SL",                # M2货币供应
    "gdp_real": "GDPC1",                # 实际GDP
    "industrial_production": "INDPRO",  # 工业生产指数
    "retail_sales": "RSAFS",            # 零售销售
    "housing_starts": "HOUST",          # 新屋开工
    "fed_funds_rate": "DFEDTARU",       # 联邦基金目标利率（上限）
    "jolts_openings": "JTSJOL",         # JOLTS职位空缺
    "avg_hourly_earnings": "CES0500000003", # 平均时薪同比
    "ism_manufacturing": "NAPM",        # ISM制造业PMI
}

# FRED 数据到系统内部字段的映射
FRED_TO_INTERNAL = {
    "PCEPI": "pce_index_yoy",
    "CPIAUCSL": "cpi_index_yoy",
    "PCEPILFE": "core_pce_yoy",
    "UNRATE": "unemployment_rate_u3",
    "PAYEMS": "nonfarm_payrolls",
    "DTB3": "treasury_yield_3m",
    "DGS2": "treasury_yield_2y",
    "DGS10": "treasury_yield_10y",
    "VIXCLS": "vix_index",
    "M2SL": "m2_supply",
    "GDPC1": "gdp_real",
    "DFEDTARU": "fed_funds_rate",
    "JTSJOL": "jolts_openings",
    "CES0500000003": "avg_hourly_earnings",
    "NAPM": "ism_manufacturing",
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
    # 衍生指标
    yield_curve_2s10s: Optional[float] = None       # 2s10s利差
    yield_curve_3m10y: Optional[float] = None       # 3m10y利差
    real_rate_3m: Optional[float] = None              # 实际利率（3m-核心PCE）
    
    def to_dataframe(self) -> pd.DataFrame:
        """转为原始项目期望的 df_macro 格式"""
        return pd.DataFrame([{
            "meeting_date": self.meeting_date,
            "info_cutoff_datetime": self.meeting_date,
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
            "white_house_party": "Republican",  # 2026
            "previous_fftr_target": int((self.fed_funds_rate or 0) * 100),
            "previous_change": 0,
        }])


@dataclass
class FedWatchSnapshot:
    """CME FedWatch 利率预期数据"""
    meeting_date: str
    probabilities: Dict[str, float] = field(default_factory=dict)  # {"325-350": 45.2, "350-375": 54.8}
    implied_rate: Optional[float] = None
    implied_action: str = ""  # "HOLD" / "HIKE" / "CUT"
    market_sentiment: str = ""


class FedDataFetcher:
    """美联储数据获取器 - FRED + CME FedWatch"""
    
    def __init__(self, fred_api_key: Optional[str] = None):
        self.fred_key = fred_api_key or os.getenv("FRED_API_KEY", "")
        self.fred_base = "https://api.stlouisfed.org/fred"
        
    # ─── FRED API ──────────────────────────────────────────
    
    def fetch_fred_series(self, series_id: str, lookback_months: int = 6) -> pd.Series:
        """获取单个 FRED 时间序列"""
        url = f"{self.fred_base}/series/observations"
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=lookback_months * 32)).strftime("%Y-%m-%d")
        
        params = {
            "series_id": series_id,
            "api_key": self.fred_key,
            "file_type": "json",
            "observation_start": start_date,
            "observation_end": end_date,
            "sort_order": "desc",
        }
        
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            observations = data.get("observations", [])
            values = []
            dates = []
            for obs in observations:
                if obs["value"] != ".":
                    values.append(float(obs["value"]))
                    dates.append(obs["date"])
            series = pd.Series(values, index=pd.to_datetime(dates))
            series.sort_index(inplace=True)  # 升序排列
            return series
        except Exception as e:
            print(f"  [WARN] FRED {series_id} fetch failed: {e}")
            return pd.Series(dtype=float)
    
    @staticmethod
    def calc_yoy(series: pd.Series, months_back: int = 12) -> pd.Series:
        """计算同比变化率 (year-over-year % change)
        
        对于月度数据: months_back=12
        对于季度数据: months_back=12 (自动匹配)
        """
        if len(series) < months_back:
            return pd.Series(dtype=float)
        # 假设月度数据，往前推 months_back 个月
        yoy = pd.Series(dtype=float)
        for idx in series.index:
            ref_date = idx - pd.DateOffset(months=months_back)
            # 找最近的值
            before = series[series.index <= ref_date]
            if not before.empty:
                old_val = before.iloc[-1]
                new_val = series.loc[idx]
                if old_val and old_val != 0:
                    yoy.loc[idx] = (new_val / old_val - 1) * 100
        yoy.sort_index(ascending=False, inplace=True)
        return yoy
    
    @staticmethod
    def calc_diff_yoy(series: pd.Series, months_back: int = 12) -> pd.Series:
        """计算差值的同比变化（用于已为百分比的指标，如收益率变化）"""
        if len(series) < months_back:
            return pd.Series(dtype=float)
        result = pd.Series(dtype=float)
        for idx in series.index:
            ref_date = idx - pd.DateOffset(months=months_back)
            before = series[series.index <= ref_date]
            if not before.empty:
                old_val = before.iloc[-1]
                new_val = series.loc[idx]
                result.loc[idx] = new_val - old_val
        result.sort_index(ascending=False, inplace=True)
        return result
    
    # 需要计算YoY的指数型序列
    YOY_SERIES = {"pce_index_yoy", "cpi_index_yoy", "core_pce_yoy", "nonfarm_payrolls", "avg_hourly_earnings"}
    
    def fetch_all_macro(self, as_of_date: Optional[str] = None) -> Dict[str, pd.Series]:
        """批量获取所有FRED宏观数据（指数型序列计算YoY%）"""
        results = {}
        print(f"\n[FRED] Fetching macro data...")
        for internal, series_id in FRED_SERIES.items():
            try:
                # 需要计算YoY的序列拉14个月
                lookback = 14 if internal in self.YOY_SERIES else 6
                series = self.fetch_fred_series(series_id, lookback_months=lookback)
                if not series.empty:
                    # 指数型序列计算YoY%
                    if internal in self.YOY_SERIES:
                        yoy = self.calc_yoy(series, months_back=12)
                        if not yoy.empty:
                            latest = yoy.iloc[0]
                            latest_date = yoy.index[0].strftime("%Y-%m-%d")
                            results[internal] = yoy
                            print(f"  OK {series_id}: {latest:.2f}% YoY (as of {latest_date})")
                        else:
                            print(f"  -- {series_id}: Cannot compute YoY")
                    else:
                        latest = series.iloc[0]
                        latest_date = series.index[0].strftime("%Y-%m-%d")
                        results[internal] = series
                        print(f"  OK {series_id}: {latest:.2f} (as of {latest_date})")
                else:
                    print(f"  -- {series_id}: No data")
            except Exception as e:
                print(f"  ERR {series_id}: {e}")
        return results
    
    def build_macro_snapshot(
        self, 
        meeting_date: str,
        data_cache: Optional[Dict[str, pd.Series]] = None
    ) -> MacroSnapshot:
        """构建指定日期的宏观快照"""
        if data_cache is None:
            data_cache = self.fetch_all_macro()
        
        def get_latest(series: pd.Series, ref_date: str) -> Optional[float]:
            """获取参考日期前最新值"""
            cutoff = pd.to_datetime(ref_date)
            valid = series[series.index <= cutoff]
            return float(valid.iloc[0]) if not valid.empty else None
        
        snap = MacroSnapshot(meeting_date=meeting_date)
        
        mapping = {
            "pce_index_yoy": "pce_yoy",
            "cpi_index_yoy": "cpi_yoy",
            "core_pce_yoy": "core_pce_yoy",
            "unemployment_rate_u3": "unemployment_rate",
            "nonfarm_payrolls": "nonfarm_payrolls",
            "treasury_yield_3m": "treasury_3m",
            "treasury_yield_2y": "treasury_2y",
            "treasury_yield_10y": "treasury_10y",
            "vix_index": "vix",
            "fed_funds_rate": "fed_funds_rate",
            "gdp_real": "gdp_real",
            "jolts_openings": "jolts_openings",
            "avg_hourly_earnings": "avg_hourly_earnings_yoy",
            "ism_manufacturing": "ism_manufacturing",
        }
        
        for src, dst in mapping.items():
            if src in data_cache:
                val = get_latest(data_cache[src], meeting_date)
                setattr(snap, dst, val)
        
        # 衍生指标
        if snap.treasury_2y and snap.treasury_10y:
            snap.yield_curve_2s10s = snap.treasury_10y - snap.treasury_2y
        if snap.treasury_3m and snap.treasury_10y:
            snap.yield_curve_3m10y = snap.treasury_10y - snap.treasury_3m
        if snap.treasury_3m and snap.core_pce_yoy:
            snap.real_rate_3m = snap.treasury_3m - snap.core_pce_yoy
        
        return snap
    
    # ─── FedWatch via yfinance + FRED ─────────────────────
    
    def fetch_fedwatch(self) -> FedWatchSnapshot:
        """从 yfinance (ZQ futures) + FRED (FF) 获取市场利率预期"""
        print(f"\n[FedWatch] Fetching rate expectations...")
        
        snapshot = FedWatchSnapshot(
            meeting_date=datetime.now().strftime("%Y-%m-%d"),
        )
        
        # 方案1: FRED FF series (联邦基金期货隐含利率, 最可靠)
        ff_series = self.fetch_fred_series("FF", lookback_months=3)
        if not ff_series.empty:
            ff_rate = float(ff_series.iloc[0])
            snapshot.implied_rate = ff_rate
            snapshot.probabilities["FRED_FF_implied"] = 100.0
            print(f"  OK FRED FF: {ff_rate:.2f}%")
        
        # 方案2: yfinance ZQ=F (30-day Fed Funds futures)
        if HAS_YFINANCE:
            try:
                zq = yf.Ticker("ZQ=F")
                hist = zq.history(period="5d")
                if not hist.empty and ff_series.empty:
                    price = float(hist['Close'].iloc[-1])
                    implied = 100 - price
                    snapshot.implied_rate = snapshot.implied_rate or implied
                    print(f"  OK ZQ=F: Price={price:.2f}, Implied={implied:.2f}%")
            except Exception as e:
                print(f"  -- yfinance ZQ=F: {e}")
                # 尝试用yfinance下载功能
                try:
                    data = yf.download("ZQ=F", period="5d", progress=False)
                    if not data.empty:
                        price = float(data['Close'].iloc[-1])
                        implied = 100 - price
                        snapshot.implied_rate = snapshot.implied_rate or implied
                        print(f"  OK ZQ=F(download): Price={price:.2f}, Implied={implied:.2f}%")
                except:
                    pass
        
        # 对比当前有效利率
        dff_series = self.fetch_fred_series("DFF", lookback_months=1)
        current_rate = None
        if not dff_series.empty:
            current_rate = float(dff_series.iloc[0])
            print(f"  OK DFF (current): {current_rate:.2f}%")
        
        # 判断市场预期
        if snapshot.implied_rate and current_rate:
            diff = snapshot.implied_rate - current_rate
            if diff > 0.15:
                snapshot.implied_action = "HIKE"
                snapshot.market_sentiment = f"Market expects ~{abs(diff):.0f}bp HIKE (implied: {snapshot.implied_rate:.2f}% vs current: {current_rate:.2f}%)"
            elif diff < -0.15:
                snapshot.implied_action = "CUT"
                snapshot.market_sentiment = f"Market expects ~{abs(diff):.0f}bp CUT (implied: {snapshot.implied_rate:.2f}% vs current: {current_rate:.2f}%)"
            else:
                snapshot.implied_action = "HOLD"
                snapshot.market_sentiment = f"Market expects HOLD (implied: {snapshot.implied_rate:.2f}%, current: {current_rate:.2f}%)"
        elif snapshot.implied_rate:
            snapshot.market_sentiment = f"Implied rate: {snapshot.implied_rate:.2f}%"
        else:
            snapshot.market_sentiment = "Rate expectation data unavailable"
        
        print(f"  ======> Action: {snapshot.implied_action} | {snapshot.market_sentiment}")
        return snapshot
    
    # ─── 综合报告 ──────────────────────────────────────────
    
    def get_full_snapshot(
        self, 
        meeting_date: Optional[str] = None
    ) -> Tuple[MacroSnapshot, FedWatchSnapshot]:
        """获取完整数据快照（宏观+FedWatch）"""
        if meeting_date is None:
            meeting_date = datetime.now().strftime("%Y-%m-%d")
        
        print(f"\n{'='*60}")
        print(f"  FedSight AI - 实时数据获取")
        print(f"  日期: {meeting_date}")
        print(f"{'='*60}")
        
        # 并行获取
        macro_data = self.fetch_all_macro(as_of_date=meeting_date)
        macro = self.build_macro_snapshot(meeting_date, macro_data)
        fedwatch = self.fetch_fedwatch()
        
        return macro, fedwatch


# ─── CLI ──────────────────────────────────────────────────

if __name__ == "__main__":
    fetcher = FedDataFetcher()
    macro, fw = fetcher.get_full_snapshot()
    
    print(f"\n{'='*60}")
    print(f"  📊 宏观数据汇总")
    print(f"{'='*60}")
    print(f"\n  【通胀】")
    print(f"    PCE同比: {macro.pce_yoy or 'N/A'}%")
    print(f"    核心PCE: {macro.core_pce_yoy or 'N/A'}%")
    print(f"    CPI同比: {macro.cpi_yoy or 'N/A'}%")
    print(f"\n  【就业】")
    print(f"    失业率: {macro.unemployment_rate or 'N/A'}%")
    print(f"    JOLTS职位空缺: {macro.jolts_openings or 'N/A'}M")
    print(f"\n  【利率市场】")
    print(f"    联邦基金利率: {macro.fed_funds_rate or 'N/A'}%")
    print(f"    3月国债: {macro.treasury_3m or 'N/A'}%")
    print(f"    2年国债: {macro.treasury_2y or 'N/A'}%")
    print(f"    10年国债: {macro.treasury_10y or 'N/A'}%")
    print(f"    2s10s利差: {macro.yield_curve_2s10s or 'N/A'}bps")
    print(f"    实际利率(3m-核心PCE): {macro.real_rate_3m or 'N/A'}%")
    print(f"\n  【风险指标】")
    print(f"    VIX: {macro.vix or 'N/A'}")
    print(f"    ISM制造业PMI: {macro.ism_manufacturing or 'N/A'}")
    print(f"\n  【CME FedWatch】")
    print(f"    隐含利率: {fw.implied_rate or 'N/A'} bps")
    print(f"    {fw.market_sentiment}")
