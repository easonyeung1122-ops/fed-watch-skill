# FedSight AI — 美联储 FOMC 利率预测 Skill

基于多Agent系统模拟FOMC（美联储公开市场委员会）决策过程，预测联邦基金利率走向。
结合 FRED 实时宏观数据 + CME FedWatch 市场预期 + LLM多角色辩论。

## 触发条件

当用户提到以下关键词时自动启用：
- "美联储"、"Fed"、"FOMC"、"加息"、"降息"、"利率决议"、"联邦基金利率"
- "预测利率"、"下一次FOMC"、"利率走向"
- "fed watch"、"fed predict"、"fed forecast"

## 功能概述

### 工作流程

```
1. 实时数据获取 → 2. Agent辩论模拟 → 3. 利率预测输出
```

| 步骤 | 组件 | 说明 |
|------|------|------|
| **数据获取** | `fed_data.py` | FRED API → 14项宏观指标 + CME FedWatch → 市场利率预期概率 |
| **分析师** | LLM Agent | 解读期货市场隐含概率，形成市场基准预期 |
| **经济学家** | LLM Agent | 基于宏观数据提出三个政策选项（鸽/中/鹰） |
| **FOMC委员×N** | LLM Agent × N | 三种原型（务实派/学术派/决策者），Chain-of-Draft推理，投票 |
| **声明起草** | LLM Agent | 模拟FOMC官方声明 |
| **报告输出** | Markdown | 预测行动、预期变动bps、投票分布、委员立场、置信度 |

### 核心Agent原型

| 原型 | 特征 | 代表委员 |
|------|------|---------|
| 🏛 区域务实派 | 重视褐皮书地方数据，数据模糊时倾向维持现状 | Bowman, Bostic, Schmid |
| 🎓 学术平衡派 | 强调通胀预期和宏观理论一致性 | Jefferson, Cook, Daly |
| ⭐ 中央决策者 | 优先委员会共识和市场稳定 | Powell, Waller, Williams |

## 使用方法

### 前置条件

1. **安装依赖**：
```bash
pip install pandas numpy openai requests beautifulsoup4 fredapi python-dotenv rich pyyaml
```

2. **配置API密钥**：复制 `.env.example` 为 `.env` 并填入：
   - `OPENAI_API_KEY`（必需，用于多Agent模拟）
   - `FRED_API_KEY`（可选，免费注册 https://fred.stlouisfed.org/docs/api/api_key.html）
   - `LLM_MODEL`（可选，默认 gpt-4o，可用 deepseek-chat 等替代）

### 模式一：实时数据模式（需FRED_API_KEY）

```bash
python run_fed_watch.py --members 5 --output report.md
```

参数说明：
- `--model`: LLM模型 (默认 gpt-4o)
- `--members`: 模拟委员数 1-12 (默认5，完整版用12更准确但耗时更长)
- `--output/-o`: 输出报告路径
- `--no-live`: 跳过实时数据，手动输入

### 模式二：手动输入模式（无需FRED_API_KEY）

```bash
python run_fed_watch.py --no-live --members 3
```

然后按提示输入宏观经济数据、FedWatch数据。

### 模式三：仅数据获取

```bash
python fed_data.py
```

仅拉取并显示当前FRED宏观数据 + CME FedWatch预期。

### 模式四：编程调用

```python
from run_fed_watch import format_macro_for_llm, format_fedwatch_for_llm
from fed_data import FedDataFetcher
from fed_sim import FOMCSimulation, run_simulation

# 获取实时数据
fetcher = FedDataFetcher(fred_api_key="your_key")
macro, fw = fetcher.get_full_snapshot()

# 运行模拟
result = run_simulation(
    macro_text=format_macro_for_llm(macro),
    fedwatch_text=format_fedwatch_for_llm(fw),
    num_members=12,  # 完整版
)

# 查看结果
print(result.predicted_action)  # HOLD / HIKE / CUT
print(result.predicted_bps)     # 预期变动bp数
print(result.confidence)        # HIGH / MEDIUM / LOW
```

## 数据来源

| 数据 | 来源 | 频率 |
|------|------|------|
| PCE/核心PCE | FRED (BEA) | 月度 |
| CPI | FRED (BLS) | 月度 |
| 失业率 | FRED (BLS) | 月度 |
| 非农就业 | FRED (BLS) | 月度 |
| 国债收益率(3m/2y/10y) | FRED (Treasury) | 日度 |
| VIX | FRED (CBOE) | 日度 |
| 联邦基金利率 | FRED (Fed) | 日度 |
| GDP | FRED (BEA) | 季度 |
| ISM PMI | FRED | 月度 |
| 利率预期概率 | CME FedWatch | 实时 |

## 输出示例

```markdown
# 🏛️ FedSight AI — FOMC利率预测报告
**日期**: 2026-07-28
**模型**: gpt-4o
**置信度**: HIGH

## 📊 预测结果

| 指标 | 结果 |
|------|------|
| **预测行动** | **HOLD** |
| **预期变动** | **+0 bps** |
| **置信度** | HIGH |

### 投票分布 (共5位委员)

| 立场 | 票数 | 占比 |
|------|------|------|
| ⚖️ HOLD | 4 | 80% |
| 🕊️ CUT | 1 | 20% |
| 🦅 HIKE | 0 | 0% |
```

## 局限性

1. **数据滞后**: FRED数据有1-2个月发布延迟
2. **无褐皮书/点阵图**: 当前版本未接入美联储褐皮书全文和SEP点阵图PDF解析
3. **成本**: GPT-4o每次完整模拟(12委员)约消耗50K-100K tokens
4. **不预测紧急会议**: 仅预测定期FOMC会议
5. **参考性质**: 所有预测仅供参考，不构成投资建议

## 推荐扩展

- 接入美联储褐皮书RSS → 自动提取最新一期全国摘要
- 解析SEP PDF → 提取点阵图分布
- 集成 RAG → 检索历史FOMC声明用于In-Context Learning
- 定时任务 → 每次FOMC会议前自动运行并推送预测

## 论文引用

> Hou, Y. et al. (2025). "FedSight AI: Multi-Agent System Architecture for Federal Funds Target Rate Prediction." NeurIPS 2025 Workshop.
>
> 实现: Craig Chirinda (https://github.com/chirindaopensource)
