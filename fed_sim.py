"""
FedSight AI - 多Agent FOMC模拟引擎
模拟: 分析师 → 经济学家 → 12位FOMC委员 → 投票 → 利率预测
每次启动自动从 federalreservehistory.org 获取最新理事会成员名单
"""
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ─── Agent 角色定义 ────────────────────────────────────────

FOMC_ARCHETYPES = {
    "Regional Pragmatist": (
        "你是区域务实派(Regional Pragmatist)。你重视地方经济反馈和褐皮书的质化信号，"
        "依赖实地数据和商业接触报告。当数据模糊时，你倾向于维持现状。"
    ),
    "Academic Balancer": (
        "你是学术平衡派(Academic Balancer)。你强调通胀预期、宏观理论一致性和前瞻性信号。"
        "你重视模型的连贯性，当通胀偏离目标时会积极主张调整。"
    ),
    "Central Policymaker": (
        "你是中央决策者(Central Policymaker)。你优先考虑委员会共识、制度信誉和市场稳定。"
        "你倾向于避免不必要的市场意外，除非有强有力的理由才改变政策。"
    ),
}


# ─── Auto-load real Board members ─────────────────────────

def _load_fomc_members() -> List[Dict]:
    """加载FOMC成员名单：优先在线获取，失败则用后备名单"""
    try:
        # 尝试导入自动更新模块
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        if skill_dir not in sys.path:
            sys.path.insert(0, skill_dir)
        from fetch_board import fetch_board_members as _fetch
        
        print(f"\n  [FOMC Loader] Auto-updating Board member list...")
        board = _fetch()
        if board and len(board) >= 5:
            members = []
            for m in board:
                members.append({
                    "name": m["name"],
                    "archetype": m["archetype"],
                    "role": m["role"],
                })
            print(f"  [FOMC Loader] Loaded {len(members)} real Board members.")
            return members
    except Exception as e:
        print(f"  [FOMC Loader] Auto-update failed: {e}")
    
    # Fallback: 2026年7月已知真实配置
    print("  [FOMC Loader] Using fallback: 2026-07 Board (Warsh as Chair)")
    return [
        {"name": "Kevin Warsh", "archetype": "Central Policymaker", "role": "Chair"},
        {"name": "Philip Jefferson", "archetype": "Academic Balancer", "role": "Vice Chair"},
        {"name": "Michelle Bowman", "archetype": "Regional Pragmatist", "role": "Vice Chair Supervision"},
        {"name": "Michael Barr", "archetype": "Academic Balancer", "role": "Governor"},
        {"name": "Lisa Cook", "archetype": "Academic Balancer", "role": "Governor"},
        {"name": "Jerome Powell", "archetype": "Central Policymaker", "role": "Governor"},
        {"name": "Christopher Waller", "archetype": "Central Policymaker", "role": "Governor"},
    ]


FOMC_MEMBERS = _load_fomc_members()


@dataclass
class AgentResult:
    """单个Agent的输出"""
    agent_name: str
    role: str
    archetype: str
    vote: str = ""          # "HIKE" / "HOLD" / "CUT"
    vote_bps: int = 0        # 预期变动bp数
    rationale: str = ""
    chain_of_thought: str = ""


@dataclass  
class SimulationResult:
    """完整模拟结果"""
    meeting_date: str
    macro_summary: str
    fedwatch_summary: str
    analyst_view: str = ""
    economist_options: str = ""
    member_results: List[AgentResult] = field(default_factory=list)
    final_vote: Dict[str, int] = field(default_factory=dict)
    predicted_action: str = ""
    predicted_bps: int = 0
    confidence: str = ""
    summary: str = ""
    

class FOMCSimulation:
    """FOMC多Agent利率决策模拟"""
    
    def __init__(self, model: str = None, base_url: str = None):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("请设置 OPENAI_API_KEY 环境变量")
        
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o")
        base = base_url or os.getenv("OPENAI_BASE_URL")
        self.client = OpenAI(
            api_key=api_key,
            base_url=base if base else None,
        )
    
    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """调用LLM"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [LLM Error] {e}")
            return f"[Error: {e}]"
    
    # ─── Step 1: Macro Analyst (Pure data, no futures bias) ──
    
    def run_analyst(self, macro_text: str, fedwatch_text: str = "") -> str:
        """宏观分析师：纯粹基于经济数据分析，不参考期货市场概率"""
        print("  [Analyst] Analyzing macro conditions (no futures bias)...")
        
        system = """你是FOMC的宏观经济分析师。你的任务是纯粹基于宏观经济数据，
分析当前经济状况、通胀压力、劳动力市场趋势和金融条件。
你不参考任何市场价格或期货隐含概率——只分析基本面数据。"""
        
        prompt = f"""请纯粹基于以下宏观经济数据分析当前经济格局：

### 宏观经济数据：
{macro_text}

### 请从以下维度分析（不参考任何市场价格）：
1. **通胀评估**：相对2%目标的位置、趋势方向、粘性来源
2. **劳动力市场**：紧张程度、工资压力、供需平衡
3. **实体经济**：增长动能、消费韧性、制造业vs服务业分化
4. **金融条件**：实际利率水平、收益率曲线形态、信贷环境
5. **核心矛盾**：当前宏观数据中最大的张力/两难是什么？

### 输出格式：
- 通胀评分: [显著高于目标 / 接近目标 / 低于目标] — [上升/回落/稳定]趋势
- 劳动力市场: [过热 / 紧张 / 平衡 / 疲软]
- 经济增长: [强劲 / 稳健 / 放缓 / 收缩]
- 核心矛盾: [1-2句话总结最大的政策两难]
- 风险平衡: [上行风险为主 / 大致平衡 / 下行风险为主]
"""
        result = self._call_llm(system, prompt)
        print(f"    完成")
        return result
    
    # ─── Step 2: Economist (Macro-only, no market input) ──
    
    def run_economist(self, macro_text: str, beige_book: str, dot_plot: str, analyst_view: str = "") -> str:
        """首席经济学家：基于宏观基本面+褐皮书+点阵图制定政策选项，不参考市场定价"""
        print("  [Economist] Formulating policy options (macro-only)...")
        
        system = """你是FOMC的首席经济学家。基于纯粹宏观经济基本面、褐皮书质化信号和点阵图，
提出三个政策选项（鸽派/中性/鹰派）。你不参考期货市场价格或隐含概率——
你的判断完全基于经济数据和美联储双重使命（最大就业+物价稳定）。"""
        
        prompt = f"""基于以下数据，为即将到来的FOMC会议制定三个政策选项：

### 宏观经济数据：
{macro_text}

### 褐皮书摘要：
{beige_book or "本期无褐皮书数据"}

### 点阵图：
{dot_plot or "本期无点阵图数据"}

### 宏观分析摘要：
{analyst_view or "无"}

### 请提出三个政策选项：
**选项A（鸽派—降息/宽松）**：
- 建议利率变动: [X] bps
- 核心逻辑: [1-2句话，引用具体数据说明为何需要宽松]

**选项B（中性—维持现状）**：
- 建议利率变动: 0 bps  
- 核心逻辑: [1-2句话，引用具体数据说明为何维持平衡]

**选项C（鹰派—加息/紧缩）**：
- 建议利率变动: [X] bps
- 核心逻辑: [1-2句话，引用具体数据说明为何需要紧缩]
"""
        result = self._call_llm(system, prompt)
        print(f"    完成")
        return result
    
    # ─── Step 3: FOMC Member Voting (Macro-only, no futures) ──
    
    def run_member(
        self, 
        member: dict, 
        macro_text: str,
        beige_book: str,
        dot_plot: str,
        economist_options: str
    ) -> AgentResult:
        """单个FOMC委员审议和投票（Chain-of-Draft推理，纯宏观数据驱动）"""
        name = member["name"]
        archetype = member["archetype"]
        persona = FOMC_ARCHETYPES[archetype]
        
        print(f"  [{name}] ({archetype}) Deliberating...")
        
        system = f"""{persona}

你正在参加FOMC政策辩论。你不是AI助手，而是一位有特定经济哲学的政策制定者。
你的决策必须纯粹基于宏观经济基本面——通胀、就业、增长、金融条件。
你不参考任何期货市场价格或市场隐含概率。
请采用Chain-of-Draft推理方式，先在草稿阶段分步分析，再汇总为最终决定。

### 关键约束：
- 每个分析步骤不超过30词
- 必须基于提供的数据做决策
- 保守主义是被允许的——数据模糊时维持现状
- 禁止参考期货市场或CME FedWatch数据"""
        
        prompt = f"""### 经济数据快照：
{macro_text}

### 褐皮书摘要：
{beige_book or "本期无褐皮书数据"}

### 点阵图：
{dot_plot or "本期无点阵图数据"}

### 经济学家选项：
{economist_options}

### 任务：Chain-of-Draft (CoD) 推理

**Phase 1 — 草稿（每步≤30词）：**
Step 1 — 通胀分析（相对2%目标）: 
Step 2 — 劳动力市场分析: 
Step 3 — 褐皮书质化信号整合: 
Step 4 — 点阵图体现的委员会分散度: 
Step 5 — 对比选项A/B/C并做选择: 

**Phase 2 — 修订：**
综合以上分析，形成最终判断。

**Phase 3 — 投票：**
- 投票: [Option A / Option B / Option C]
- 隐含行动: [HOLD / HIKE XX bps / CUT XX bps]  
- 核心理由: [一段话]"""
        
        response = self._call_llm(system, prompt, temperature=0.4)
        
        # 解析投票
        vote = "HOLD"
        vote_bps = 0
        
        if "CUT" in response.upper():
            vote = "CUT"
            import re
            bps_match = re.search(r'CUT\s*(\d+)', response.upper())
            if bps_match:
                vote_bps = -int(bps_match.group(1))
            else:
                vote_bps = -25
        elif "HIKE" in response.upper():
            vote = "HIKE"
            import re
            bps_match = re.search(r'HIKE\s*(\d+)', response.upper())
            if bps_match:
                vote_bps = int(bps_match.group(1))
            else:
                vote_bps = 25
        
        # 提取投票选项
        if "Option A" in response:
            vote = "CUT" if "鸽" in economist_options or "Dovish" in economist_options else "HOLD"
        elif "Option C" in response:
            vote = "HIKE" if "鹰" in economist_options or "Hawkish" in economist_options else "HOLD"
        
        result = AgentResult(
            agent_name=name,
            role=member["role"],
            archetype=archetype,
            vote=vote,
            vote_bps=vote_bps,
            rationale=response[-300:] if len(response) > 300 else response,
            chain_of_thought=response[:500] if len(response) > 500 else response,
        )
        
        print(f"    Vote: {vote} ({vote_bps:+d}bps)")
        return result
    
    # ─── Step 4: Statement Drafter ────────────────────────
    
    def run_statement_drafter(self, voting_record: str, majority_rationale: str) -> str:
        """模拟FOMC声明"""
        print("  [Chair] Drafting FOMC statement...")
        
        system = """你是FOMC主席。请以美联储官方声明的正式、精确、中性口吻，
起草一份模拟的FOMC会议声明。"""
        
        prompt = f"""### 投票记录：
{voting_record}

### 多数派理由：
{majority_rationale}

### 请起草FOMC声明：
1. 清晰声明联邦基金利率决定
2. 总结支持该决策的经济展望
3. 承认风险平衡
4. 保持正式、精确、中性的官方沟通口吻"""
        
        return self._call_llm(system, prompt)
    
    # ─── Main Pipeline ────────────────────────────────────
    
    def run(
        self,
        macro_text: str,
        fedwatch_text: str = "",
        beige_book: str = "",
        dot_plot: str = "",
        verbose: bool = True,
        num_members: int = 5,
    ) -> SimulationResult:
        """执行完整FOMC模拟（Agent投票不依赖Fed Funds期货）"""
        
        print(f"\n{'='*60}")
        print(f"  FedSight AI - FOMC Simulation Start")
        print(f"  Model: {self.model}")
        print(f"  Members: {num_members}")
        print(f"  Mode: Macro-only (no futures bias)")
        print(f"{'='*60}\n")
        
        result = SimulationResult(
            meeting_date=datetime.now().strftime("%Y-%m-%d"),
            macro_summary=macro_text[:500],
            fedwatch_summary=fedwatch_text[:500] if fedwatch_text else "",
        )
        
        # Step 1: Macro Analyst (pure data, no futures)
        result.analyst_view = self.run_analyst(macro_text)
        
        # Step 2: Economist (macro + beige book + dot plot, NO FedWatch)
        result.economist_options = self.run_economist(
            macro_text, beige_book, dot_plot, result.analyst_view
        )
        
        # Step 3: Members vote (macro-only, no fedwatch_text passed in)
        members_to_run = FOMC_MEMBERS[:num_members]
        for member in members_to_run:
            member_result = self.run_member(
                member, macro_text, beige_book, dot_plot,
                result.economist_options
            )
            result.member_results.append(member_result)
        
        # Tally votes
        votes = {"HIKE": 0, "HOLD": 0, "CUT": 0}
        total_bps = 0
        for mr in result.member_results:
            votes[mr.vote] += 1
            total_bps += mr.vote_bps
        
        result.final_vote = votes
        
        # Determine action
        max_vote = max(votes, key=votes.get)
        result.predicted_action = max_vote
        result.predicted_bps = round(total_bps / len(result.member_results)) if result.member_results else 0
        
        # Confidence
        majority_pct = votes[max_vote] / len(result.member_results) * 100
        if majority_pct >= 75:
            result.confidence = "HIGH"
        elif majority_pct >= 60:
            result.confidence = "MEDIUM"
        else:
            result.confidence = "LOW"
        
        # Draft statement
        voting_record = f"Hawkish(HIKE): {votes['HIKE']}, Neutral(HOLD): {votes['HOLD']}, Dovish(CUT): {votes['CUT']}"
        majority_rationales = "\n".join([
            f"- {mr.agent_name} ({mr.archetype}): {mr.rationale[:100]}"
            for mr in result.member_results if mr.vote == max_vote
        ])
        result.summary = self.run_statement_drafter(voting_record, majority_rationales)
        
        return result
    
    def format_report(self, result: SimulationResult) -> str:
        """格式化输出预测报告"""
        
        lines = []
        lines.append(f"# 🏛️ FedSight AI — FOMC利率预测报告")
        lines.append(f"**日期**: {result.meeting_date}")
        lines.append(f"**模型**: {self.model}")
        lines.append(f"**模式**: 纯宏观基本面驱动（Agent不参考期货市场概率）")
        lines.append(f"**置信度**: {result.confidence}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 📊 预测结果")
        lines.append("")
        lines.append(f"| 指标 | 结果 |")
        lines.append(f"|------|------|")
        lines.append(f"| **预测行动** | **{result.predicted_action}** |")
        lines.append(f"| **预期变动** | **{result.predicted_bps:+d} bps** |")
        lines.append(f"| **置信度** | {result.confidence} |")
        lines.append("")
        lines.append(f"### 投票分布 (共{len(result.member_results)}位委员)")
        lines.append("")
        lines.append(f"| 立场 | 票数 | 占比 |")
        lines.append(f"|------|------|------|")
        for action, count in result.final_vote.items():
            pct = count / len(result.member_results) * 100
            emoji = "🦅" if action == "HIKE" else ("🕊️" if action == "CUT" else "⚖️")
            lines.append(f"| {emoji} {action} | {count} | {pct:.0f}% |")
        lines.append("")
        lines.append("### 各委员投票")
        lines.append("")
        lines.append(f"| 委员 | 角色 | 类型 | 投票 |")
        lines.append(f"|------|------|------|------|")
        for mr in result.member_results:
            emoji = "🦅" if mr.vote == "HIKE" else ("🕊️" if mr.vote == "CUT" else "⚖️")
            lines.append(f"| {mr.agent_name} | {mr.role} | {mr.archetype} | {emoji} {mr.vote} ({mr.vote_bps:+d}bps) |")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 👨‍🏫 经济学家选项")
        lines.append("")
        lines.append(result.economist_options)
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 📝 模拟FOMC声明")
        lines.append("")
        lines.append(result.summary)
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*免责声明: 本报告由AI多Agent系统模拟生成，仅供研究参考，不构成任何投资建议。*")
        lines.append("")
        
        # Add FedWatch as external reference (not used in agent decisions)
        if result.fedwatch_summary:
            lines.append("---")
            lines.append("")
            lines.append("## 📡 市场参考（外部基准 — 未用于Agent决策）")
            lines.append("")
            lines.append("> 以下Fed Funds期货数据仅供对比参考，**未参与**FOMC委员投票决策。")
            lines.append("> Agent投票完全基于宏观经济基本面。")
            lines.append("")
            lines.append(result.fedwatch_summary)
        
        return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────

def run_simulation(
    macro_text: str,
    fedwatch_text: str = "",
    beige_book: str = "",
    dot_plot: str = "",
    model: str = None,
    num_members: int = 5,
) -> SimulationResult:
    """快捷调用"""
    sim = FOMCSimulation(model=model)
    return sim.run(
        macro_text=macro_text,
        fedwatch_text=fedwatch_text,
        beige_book=beige_book,
        dot_plot=dot_plot,
        num_members=num_members,
    )


if __name__ == "__main__":
    # 测试模式
    test_macro = """
    核心PCE同比: 2.8%
    CPI同比: 3.1%
    失业率: 4.1%
    非农新增: 180K
    联邦基金利率: 4.50-4.75%
    2年期国债: 4.25%
    10年期国债: 4.50%
    VIX: 18.5
    ISM制造业PMI: 49.2
    """
    
    test_fedwatch = """
    CME FedWatch:
    425-450: 5%
    450-475: 85%
    475-500: 10%
    隐含利率: 456 bps
    市场主导预期: 维持不变 (HOLD)
    """
    
    sim = FOMCSimulation()
    result = sim.run(
        macro_text=test_macro,
        fedwatch_text=test_fedwatch,
        num_members=3,
    )
    
    print("\n" + sim.format_report(result))
