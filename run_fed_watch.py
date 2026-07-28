"""
FedSight AI - 主入口
整合 FRED 实时数据 + CME FedWatch + 多Agent FOMC模拟
"""
import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from fed_data import FedDataFetcher, MacroSnapshot, FedWatchSnapshot
from fed_sim import FOMCSimulation, FOMC_MEMBERS


def format_macro_for_llm(macro: MacroSnapshot) -> str:
    """将MacroSnapshot格式化为LLM可读的文本"""
    lines = []
    
    # 通胀
    lines.append("## 通胀指标")
    if macro.core_pce_yoy:
        lines.append(f"- 核心PCE同比: {macro.core_pce_yoy:.1f}%  (Fed最关注的通胀指标)")
    if macro.pce_yoy:
        lines.append(f"- PCE同比: {macro.pce_yoy:.1f}%")
    if macro.cpi_yoy:
        lines.append(f"- CPI同比: {macro.cpi_yoy:.1f}%")
    
    # 就业
    lines.append("\n## 劳动力市场")
    if macro.unemployment_rate:
        lines.append(f"- 失业率(U3): {macro.unemployment_rate:.1f}%")
    if macro.nonfarm_payrolls:
        lines.append(f"- 非农新增就业: {macro.nonfarm_payrolls/1000:.0f}K")
    if macro.jolts_openings:
        lines.append(f"- JOLTS职位空缺: {macro.jolts_openings/1000:.1f}M")
    if macro.avg_hourly_earnings_yoy:
        lines.append(f"- 平均时薪同比: {macro.avg_hourly_earnings_yoy:.1f}%")
    
    # 利率与金融条件
    lines.append("\n## 利率与金融条件")
    if macro.fed_funds_rate:
        lines.append(f"- 联邦基金利率(上限): {macro.fed_funds_rate:.2f}%")
    if macro.treasury_3m:
        lines.append(f"- 3个月国债收益率: {macro.treasury_3m:.2f}%")
    if macro.treasury_2y:
        lines.append(f"- 2年期国债收益率: {macro.treasury_2y:.2f}%")
    if macro.treasury_10y:
        lines.append(f"- 10年期国债收益率: {macro.treasury_10y:.2f}%")
    if macro.yield_curve_2s10s is not None:
        signal = "倒挂⚠️" if macro.yield_curve_2s10s < 0 else "正常"
        lines.append(f"- 2s10s利差: {macro.yield_curve_2s10s:.0f}bps ({signal})")
    if macro.real_rate_3m is not None:
        lines.append(f"- 实际利率(3m-核心PCE): {macro.real_rate_3m:.1f}%")
    
    # 实体经济
    lines.append("\n## 实体经济")
    if macro.gdp_real:
        lines.append(f"- 实际GDP: {macro.gdp_real:.1f}%")
    if macro.ism_manufacturing is not None:
        signal = "收缩⚠️" if macro.ism_manufacturing < 50 else "扩张"
        lines.append(f"- ISM制造业PMI: {macro.ism_manufacturing:.1f} ({signal})")
    
    # 风险指标
    lines.append("\n## 风险指标")
    if macro.vix is not None:
        lines.append(f"- VIX波动率指数: {macro.vix:.1f}")
    
    return "\n".join(lines)


def format_fedwatch_for_llm(fw: FedWatchSnapshot) -> str:
    """将FedWatch格式化"""
    lines = ["## CME FedWatch 市场利率预期\n"]
    if fw.implied_rate:
        lines.append(f"- 隐含联邦基金利率: {fw.implied_rate:.0f} bps")
    if fw.market_sentiment:
        lines.append(f"- {fw.market_sentiment}")
    if fw.probabilities:
        lines.append("- 概率分布:")
        for r, p in sorted(fw.probabilities.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  - {r} bps: {p:.1f}%")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="FedSight AI - FOMC利率预测")
    parser.add_argument("--model", default=None, help="LLM模型名 (默认: 从.env读取或gpt-4o)")
    parser.add_argument("--members", type=int, default=5, help="模拟委员数量 (1-12)")
    parser.add_argument("--no-live", action="store_true", help="跳过实时数据获取，使用手动输入")
    parser.add_argument("--output", "-o", default=None, help="输出报告路径")
    args = parser.parse_args()
    
    # 检查API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        print("   创建 .env 文件: cp .env.example .env 然后填入你的密钥")
        sys.exit(1)
    
    # ── 获取数据 ──────────────────────────────────────────
    if args.no_live:
        print("⚠️  跳过实时数据，使用手动输入模式\n")
        macro_text = input("请输入宏观经济数据(多行, 输入END结束):\n")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        if lines:
            macro_text = "\n".join(lines)
        
        fedwatch_text = input("\n请输入FedWatch数据: ")
        beige_book = input("\n请输入褐皮书摘要(可选, 回车跳过): ")
    else:
        # 检查FRED API Key
        fred_key = os.getenv("FRED_API_KEY", "")
        if not fred_key or fred_key == "your_fred_api_key_here":
            print("⚠️  未设置 FRED_API_KEY，将使用模拟数据")
            print("   免费获取: https://fred.stlouisfed.org/docs/api/api_key.html\n")
            # 使用模拟数据
            macro_text = """## 通胀指标
- 核心PCE同比: 2.8%
- PCE同比: 2.5%
- CPI同比: 3.0%

## 劳动力市场
- 失业率(U3): 4.1%
- 非农新增就业: 180K
- JOLTS职位空缺: 8.2M

## 利率与金融条件
- 联邦基金利率(上限): 4.75%
- 2年期国债收益率: 4.20%
- 10年期国债收益率: 4.55%
- 2s10s利差: 35bps (正常)
- 实际利率(3m-核心PCE): 1.95%

## 实体经济
- ISM制造业PMI: 49.2 (收缩⚠️)

## 风险指标
- VIX波动率指数: 18.5"""
            
            fedwatch_text = """## CME FedWatch 市场利率预期
- 隐含联邦基金利率: 456 bps
- 最可能: 450-475bps (85%)
- 概率分布:
  - 425-450 bps: 5%
  - 450-475 bps: 85%
  - 475-500 bps: 10%"""
        else:
            print("📡 正在获取实时数据...")
            try:
                fetcher = FedDataFetcher(fred_api_key=fred_key)
                macro, fw = fetcher.get_full_snapshot()
                macro_text = format_macro_for_llm(macro)
                fedwatch_text = format_fedwatch_for_llm(fw)
            except Exception as e:
                print(f"❌ 数据获取失败: {e}")
                print("   使用 --no-live 手动输入数据，或检查FRED_API_KEY")
                sys.exit(1)
        
        beige_book = ""
        dot_plot = ""
    
    # ── 运行模拟 ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  🏛️  启动 FOMC 多Agent模拟")
    print(f"  Model: {args.model or os.getenv('LLM_MODEL', 'gpt-4o')}")
    print(f"  Members: {args.members}")
    print(f"{'='*60}")
    
    sim = FOMCSimulation(model=args.model)
    
    try:
        result = sim.run(
            macro_text=macro_text,
            fedwatch_text=fedwatch_text,
            beige_book=beige_book,
            num_members=args.members,
        )
    except Exception as e:
        print(f"\n❌ 模拟失败: {e}")
        sys.exit(1)
    
    # ── 生成报告 ──────────────────────────────────────────
    report = sim.format_report(result)
    
    # 添加数据来源
    data_section = f"""
---

## 📡 输入数据

### 宏观经济数据
{macro_text}

### 市场预期
{fedwatch_text}
"""
    report = report.replace("---\n\n*免责声明", data_section + "\n---\n\n*免责声明")
    
    # 输出
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {args.output}")
    
    print("\n" + report)


if __name__ == "__main__":
    main()
