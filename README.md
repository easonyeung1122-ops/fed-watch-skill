# 🏛️ FedSight AI — FOMC Rate Prediction Skill

> 基于多Agent系统的FOMC利率预测Skill，接入FRED实时宏观数据 + CME FedWatch市场预期  
> Multi-agent FOMC simulation with real-time FRED macro data + CME FedWatch market expectations

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![CodeBuddy Skill](https://img.shields.io/badge/CodeBuddy-Skill-green)](https://www.codebuddy.ai/)

---

## 📖 简介 / Overview

FedSight AI 是一个 AI 驱动的 FOMC（美联储公开市场委员会）利率决策模拟系统。它利用多个 LLM Agent 分别扮演分析师、经济学家和 FOMC 投票委员，通过 Chain-of-Draft 推理链进行辩论和投票，最终输出利率预测报告。

FedSight AI is an AI-powered FOMC (Federal Open Market Committee) rate decision simulation system. It uses multiple LLM agents playing the roles of Analyst, Economist, and FOMC voting members to debate and vote via Chain-of-Draft reasoning, producing a rate prediction report.

**论文 / Paper**: Hou et al. (2025) "FedSight AI: Multi-Agent System Architecture for Federal Funds Target Rate Prediction" — NeurIPS 2025 Workshop

---

## 🎯 核心功能 / Key Features

| 功能 Feature | 说明 Description |
|-------------|-----------------|
| 📡 **实时数据 / Real-time Data** | FRED API 获取14项宏观指标（PCE/CPI/就业/利率/VIX），自动计算同比 / 14 FRED macro indicators with auto YoY calculation |
| 🏦 **市场预期 / Market Expectations** | FRED FF + yfinance ZQ 期货获取隐含利率预期 / Implied rate from futures |
| 👥 **真实理事会 / Real Board** | 每次启动自动从 federalreservehistory.org 获取最新FOMC理事会成员 / Auto-fetches current Board members |
| 🧠 **多Agent投票 / Multi-Agent Voting** | Analyst → Economist → FOMC委员（7人）× Chain-of-Draft推理 → 投票 / 7 Governors × CoD reasoning → vote |
| 📊 **原型分类 / Archetypes** | 三种FOMC原型：⭐决策者 / 🎓学术派 / 🏛务实派 / 3 archetypes: Central Policymaker, Academic Balancer, Regional Pragmatist |
| 📝 **模拟声明 / Simulated Statement** | 自动起草FOMC官方声明 / Auto-generate FOMC press release |
| 📄 **HTML报告 / HTML Report** | 深色主题精美HTML预测报告 / Dark-themed HTML prediction report |
| 🔌 **CodeBuddy Skill** | 一键安装为CodeBuddy技能，对话即可触发 / Install as CodeBuddy Skill, trigger via chat |

---

## 🚀 快速开始 / Quick Start

### 1. 克隆仓库 / Clone

```bash
git clone https://github.com/easonyeung1122-ops/fed-watch-skill.git
cd fed-watch-skill
```

### 2. 安装依赖 / Install Dependencies

```bash
pip install pandas numpy openai requests beautifulsoup4 fredapi python-dotenv rich pyyaml yfinance
```

### 3. 配置 API Keys / Configure

```bash
cp .env.example .env
```

编辑 `.env` 文件 / Edit `.env`:

```ini
# 必需 / Required: OpenAI API Key（用于多Agent模拟 / for multi-agent simulation）
OPENAI_API_KEY=sk-your-key-here

# 可选 / Optional: FRED API Key（用于实时宏观数据 / for real-time macro data）
# 免费注册 / Free registration: https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY=your_fred_api_key_here

# 可选 / Optional: 用国产模型降低成本 / Use domestic models to reduce cost
# LLM_MODEL=deepseek-chat
# OPENAI_BASE_URL=https://api.deepseek.com
```

### 4. 运行 / Run

```bash
# 完整模拟 / Full simulation（需要 FRED_API_KEY + OPENAI_API_KEY）
python run_fed_watch.py --members 7 --output report.md

# 仅查看实时宏观数据 / View real-time macro data only
python fed_data.py

# 手动输入模式 / Manual input mode（无需 FRED Key / No FRED key needed）
python run_fed_watch.py --no-live --members 5
```

### 5. 作为 CodeBuddy Skill 安装 / Install as CodeBuddy Skill

```bash
# 复制到 CodeBuddy skills 目录 / Copy to CodeBuddy skills directory
mkdir -p ~/.codebuddy/skills/fed-watch
cp -r * ~/.codebuddy/skills/fed-watch/
```

然后在 CodeBuddy 对话中直接说：/ Then just say in CodeBuddy chat:
- "预测美联储利率" / "Predict Fed rate"
- "下一次FOMC会议" / "Next FOMC meeting"

---

## 🧠 架构 / Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    数据层 / Data Layer                    │
│  FRED API (14 indicators)  │  yfinance ZQ futures       │
│  federalreservehistory.org  │  Board auto-updater       │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  模拟层 / Simulation Layer                │
│                                                         │
│  Step 1: Analyst         →  解读市场信号 / Market read    │
│  Step 2: Economist       →  提出3个政策选项 / 3 options   │
│  Step 3: FOMC Members×7  →  Chain-of-Draft 推理+投票     │
│  Step 4: Statement       →  起草FOMC声明 / Press release │
│                                                         │
│  Archetypes / 原型:                                       │
│  ⭐ Central Policymaker   →  共识+稳定 / Consensus        │
│  🎓 Academic Balancer    →  理论+模型 / Theory-driven     │
│  🏛 Regional Pragmatist  →  数据+务实 / Data-pragmatic    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  输出层 / Output Layer                    │
│  Markdown Report  │  HTML Report  │  JSON Results        │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 输出示例 / Sample Output

```
════════════════════════════════════════════
  🏛️  FedSight AI — FOMC 利率预测
  2026-07-28 | Chair: Kevin Warsh
════════════════════════════════════════════

  📡 宏观数据 / Macro Data
  PCE YoY: 4.07% | Core PCE: 3.41% | CPI: 3.46%
  Unemployment: 4.3% | Fed Rate: 3.75%
  10y: 4.30% | 2s10s: +0.70% (normal)

  🏦 市场预期 / Market
  Implied: 3.64% vs Current: 3.63% → HOLD

  🗳️ 投票 / Vote
  ⚖️ HOLD: 7 (100%)
  🕊️ CUT:  0 (0%)
  🦅 HIKE: 0 (0%)

  🏁 预测 / Prediction: HOLD (+0 bps) | Confidence: HIGH
```

---

## 📁 项目结构 / Project Structure

```
fed-watch-skill/
├── SKILL.md                # CodeBuddy Skill 定义 / Skill definition
├── README.md               # 本文件 / This file
├── .env.example            # API Key 配置模板 / API key template
├── .gitignore
│
├── fed_data.py             # FRED + FedWatch 数据获取 / Data fetching
├── fed_sim.py              # 多Agent FOMC模拟引擎 / Simulation engine
├── fetch_board.py          # 理事会成员自动更新 / Board auto-updater
├── run_fed_watch.py        # 主入口 / Main entry point
│
├── fomc_report.html        # HTML 预测报告 / HTML prediction report
├── test_apis.py            # API 测试 / API test
├── test_board_update.py    # 理事会更新测试 / Board update test
├── check_members.py        # 成员名单检查 / Member list check
│
├── config.yaml             # 原始项目配置 / Original project config
├── requirements.txt        # 原始项目依赖 / Original requirements
└── LICENSE                 # MIT License
```

---

## 🛠️ 可用场景 / Scenarios

通过 `.env` 设置 `FOMC_CHAIR` 环境变量切换主席情景 / Switch Chair scenario via `FOMC_CHAIR` env var:

| 情景 Scenario | Chair | 描述 Description |
|:--|------|------|
| `waller` | Chris Waller | R白宫+市场导向 / Market-oriented |
| `bowman` | Michelle Bowman | R白宫+鹰派务实 / Hawkish pragmatist |
| `powell_governor` | Powell (临时/Acting) | 过渡期 / Transition period |
| `jefferson` | Philip Jefferson | D白宫+学术派 / Academic |

> **注意 / Note**: Skill会自动从 federalreservehistory.org 更新真实理事会名单，环境变量仅在上游获取失败时作为 fallback。
> The Skill auto-updates Board members from federalreservehistory.org; the env var is a fallback only.

---

## 📚 数据来源 / Data Sources

| 数据 Data | 来源 Source | 频率 Frequency |
|-----------|------------|:--:|
| PCE / 核心PCE / CPI | FRED (BEA/BLS) | Monthly |
| 失业率 / 非农 / 时薪 | FRED (BLS) | Monthly |
| 国债收益率 3m/2y/10y | FRED (Treasury) | Daily |
| VIX | FRED (CBOE) | Daily |
| 联邦基金利率 | FRED (Fed) | Daily |
| 利率期货隐含预期 | FRED FF + yfinance ZQ | Daily |
| 理事会成员名单 | federalreservehistory.org | On each run |

---

## ⚠️ 局限性 / Limitations

| 局限 Limitation | 说明 Description |
|----------------|-----------------|
| 🕐 数据滞后 / Data lag | FRED部分数据有1-2个月发布延迟 / Some FRED data has 1-2 month release lag |
| 📋 无褐皮书 / No Beige Book | 当前未接入美联储褐皮书全文 / Not yet integrated |
| 💰 成本 / Cost | GPT-4o 完整7委员模拟约消耗50K-80K tokens / ~50K-80K tokens for full 7-member sim |
| 🔮 仅预测定会议 / Scheduled only | 不预测紧急会议 / No emergency meeting prediction |
| 📖 仅供参考 / Reference only | 所有预测不构成投资建议 / Not investment advice |

---

## 🔮 计划扩展 / Roadmap

- [ ] 接入美联储褐皮书 RSS / Integrate Fed Beige Book RSS
- [ ] 解析SEP点阵图PDF / Parse SEP Dot Plot PDF
- [ ] RAG检索历史FOMC声明 / RAG for historical FOMC statements
- [ ] 定时任务自动运行 / Scheduled auto-run before each FOMC meeting
- [ ] 多语言支持 / Multi-language support
- [ ] Telegram/Discord 推送通知 / Push notifications

---

## 📄 许可 / License

MIT License — 详见 [LICENSE](LICENSE) 文件

原项目 / Original project: [chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction](https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction)

---

## 🙏 致谢 / Acknowledgments

- 论文作者 / Paper authors: Yuhan Hou, Tianji Rao, Jeremy Matthew Tan et al. (Duke University / BNY AI Hub)
- 开源实现 / Open-source implementation: Craig Chirinda
- 数据来源 / Data: FRED (Federal Reserve Bank of St. Louis), CME Group, federalreservehistory.org
