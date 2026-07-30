"""
FedSight AI - Board Members Auto-Updater
每次运行前从 federalreservehistory.org 获取最新 FOMC 理事会成员名单
并自动映射到 Agent 原型（基于公开的学术背景和政策立场）
"""
import sys
import re
from typing import List, Dict, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ─── 已知委员的原型映射（基于学术背景、历史投票和政策声明） ───
ARCHETYPE_MAP: Dict[str, str] = {
    # 2026 理事会
    "Kevin M. Warsh": "Central Policymaker",       # 前布什政府顾问，市场导向
    "Kevin Warsh": "Central Policymaker",
    "Philip N. Jefferson": "Academic Balancer",     # Duke/Columbia 经济学家
    "Philip Jefferson": "Academic Balancer",
    "Michelle W. Bowman": "Regional Pragmatist",    # 前堪萨斯银行监管官，社区银行
    "Michelle Bowman": "Regional Pragmatist",
    "Michael S. Barr": "Academic Balancer",         # 密歇根法学教授，金融监管
    "Michael Barr": "Academic Balancer",
    "Lisa D. Cook": "Academic Balancer",            # MSU 经济学家，不平等研究
    "Lisa Cook": "Academic Balancer",
    "Jerome H. Powell": "Central Policymaker",      # 前主席，共识构建者
    "Jerome Powell": "Central Policymaker",
    "Christopher J. Waller": "Central Policymaker", # 货币政策专家，市场思维
    "Christopher Waller": "Central Policymaker",
    
    # 常见 FOMC 轮值投票委员 (地区联储主席，2026年轮值)
    "John C. Williams": "Central Policymaker",       # NY Fed
    "John Williams": "Central Policymaker",
    "Raphael W. Bostic": "Regional Pragmatist",      # Atlanta Fed
    "Raphael Bostic": "Regional Pragmatist",
    "Beth M. Hammack": "Regional Pragmatist",        # Cleveland Fed
    "Beth Hammack": "Regional Pragmatist",
    "Alberto G. Musalem": "Academic Balancer",       # St. Louis Fed (new 2024)
    "Alberto Musalem": "Academic Balancer",
    "Lorie K. Logan": "Central Policymaker",         # Dallas Fed
    "Lorie Logan": "Central Policymaker",
    "Austan D. Goolsbee": "Academic Balancer",       # Chicago Fed
    "Austan Goolsbee": "Academic Balancer",
    "Susan M. Collins": "Academic Balancer",         # Boston Fed
    "Susan Collins": "Academic Balancer",
    "Mary C. Daly": "Academic Balancer",             # San Francisco Fed
    "Mary Daly": "Academic Balancer",
    "Thomas I. Barkin": "Regional Pragmatist",       # Richmond Fed
    "Thomas Barkin": "Regional Pragmatist",
    "Jeffrey R. Schmid": "Regional Pragmatist",      # Kansas City Fed
    "Jeffrey Schmid": "Regional Pragmatist",
    "Neel Kashkari": "Central Policymaker",           # Minneapolis Fed
    "Patrick T. Harker": "Academic Balancer",        # Philadelphia Fed
    "Patrick Harker": "Academic Balancer",
    "Adriana D. Kugler": "Academic Balancer",        # 前理事会成员(2023-)
    "Adriana Kugler": "Academic Balancer",
}

# 理事会职位关键词映射
ROLE_MAP = {
    "chairman": "Chair",
    "chair": "Chair",
    "vice chair for supervision": "Vice Chair Supervision",
    "vice chair": "Vice Chair",
    "governor": "Governor",
    "president": "President",  # 地区联储主席
}

# Arroyo Set 角色描述
ROLE_DESCRIPTIONS = {
    "Chair": "联邦储备委员会主席，由总统提名参议院确认，任期4年。主持FOMC会议，设定会议议程。",
    "Vice Chair": "联邦储备委员会副主席，协助主席工作，在主席缺席时代理主持。",
    "Vice Chair Supervision": "监管副主席，负责监督美联储的银行监管职能。",
    "Governor": "联邦储备委员会理事，7位理事之一，任期14年。参与FOMC投票。",
    "President": "地区联邦储备银行行长，轮值FOMC投票权。",
}

# 默认原型描述
ARCHETYPE_DESCRIPTIONS = {
    "Central Policymaker": "中央决策者。优先考虑委员会共识、制度信誉和市场稳定。倾向于避免不必要的市场意外。",
    "Regional Pragmatist": "区域务实派。重视地方经济反馈和褐皮书质化信号。依赖实地数据，数据模糊时倾向维持现状。",
    "Academic Balancer": "学术平衡派。强调通胀预期、宏观理论一致性和前瞻性信号。重视模型连贯性。",
}


def fetch_board_members(source: str = "federalreservehistory") -> List[Dict]:
    """从网络获取当前 FOMC 理事会成员名单
    
    Args:
        source: 数据源 ("federalreservehistory" 或 "fed_official")
    
    Returns:
        [{name, role, archetype, description, voting: bool}, ...]
    """
    if source == "federalreservehistory":
        return _fetch_from_frh()
    else:
        return _fetch_from_fed_official()


def _fetch_from_frh() -> List[Dict]:
    """从 federalreservehistory.org 获取数据"""
    url = "https://www.federalreservehistory.org/people/current-fed-leaders"
    print(f"  [Board Updater] Fetching from federalreservehistory.org...")
    
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        members = []
        
        # 方法1: 解析表格
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    name = cells[0].get_text(strip=True)
                    role = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    # 从年份列提取任期
                    year = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    
                    # 跳过标题行
                    if name.lower() in ("member name", "name", "member"):
                        continue
                    if not name or len(name) < 3:
                        continue
                    
                    clean_name = _clean_name(name)
                    archetype, arche_desc = _get_archetype(clean_name)
                    role_clean = _clean_role(role)
                    
                    is_voting = _is_voting_member(role_clean, clean_name)
                    
                    members.append({
                        "name": clean_name,
                        "role": role_clean,
                        "archetype": archetype,
                        "archetype_desc": arche_desc,
                        "voting": is_voting,
                        "source": "federalreservehistory.org",
                    })
        
        # 方法2: 如果表格为空，尝试从页面文本解析
        if not members:
            members = _parse_from_text(soup)
        
        if members:
            print(f"  [Board Updater] Found {len(members)} Board members")
            for m in members:
                vote_tag = "🗳️" if m["voting"] else "  "
                print(f"    {vote_tag} {m['name']:25s} | {m['role']:25s} | {m['archetype']}")
        else:
            print(f"  [Board Updater] WARNING: No members found! Using fallback.")
            members = _get_fallback_members()
        
        return members
        
    except Exception as e:
        print(f"  [Board Updater] ERROR: {e}")
        print(f"  [Board Updater] Falling back to cached member list.")
        return _get_fallback_members()


def _fetch_from_fed_official() -> List[Dict]:
    """从 federalreserve.gov 官方页面获取"""
    url = "https://www.federalreserve.gov/aboutthefed/bios/board/default.htm"
    print(f"  [Board Updater] Fetching from federalreserve.gov...")
    
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        members = []
        
        # 查找包含成员信息的 div/panel
        # Fed官网使用特定class: "panel panel-default" 或类似结构
        panels = soup.find_all("div", class_=re.compile(r"panel|bio|member", re.I))
        
        for panel in panels:
            text = panel.get_text(strip=True)
            # 尝试提取姓名和头衔
            for known_name in ARCHETYPE_MAP:
                if known_name.lower() in text.lower():
                    # 避免重复
                    if not any(m["name"] == _clean_name(known_name) for m in members):
                        archetype, _ = _get_archetype(known_name)
                        role = "Governor"
                        if "chairman" in text.lower() or "chair" in text.lower():
                            if "supervision" in text.lower():
                                role = "Vice Chair Supervision"
                            elif "vice" in text.lower():
                                role = "Vice Chair"
                            else:
                                role = "Chair"
                        members.append({
                            "name": _clean_name(known_name),
                            "role": role,
                            "archetype": archetype,
                            "archetype_desc": ARCHETYPE_DESCRIPTIONS.get(archetype, ""),
                            "voting": True,
                            "source": "federalreserve.gov",
                        })
        
        if not members:
            members = _get_fallback_members()
        
        return members
        
    except Exception as e:
        print(f"  [Board Updater] ERROR: {e}")
        return _get_fallback_members()


def _parse_from_text(soup: BeautifulSoup) -> List[Dict]:
    """从页面文本反解析成员信息"""
    text = soup.get_text()
    members = []
    
    for known_name in ARCHETYPE_MAP:
        if known_name.lower() in text.lower() and len(known_name) > 6:
            clean = _clean_name(known_name)
            if not any(m["name"] == clean for m in members):
                archetype, arche_desc = _get_archetype(clean)
                
                # 检测角色
                role = "Governor"
                # 在名字附近搜索
                idx = text.lower().find(known_name.lower())
                nearby = text[max(0,idx-100):idx+200].lower()
                if "chairman" in nearby or "chair" in nearby:
                    if "supervision" in nearby:
                        role = "Vice Chair Supervision"
                    elif "vice" in nearby:
                        role = "Vice Chair"
                    else:
                        role = "Chair"
                elif "vice chair" in nearby:
                    role = "Vice Chair"
                
                members.append({
                    "name": clean,
                    "role": role,
                    "archetype": archetype,
                    "archetype_desc": arche_desc,
                    "voting": True,
                    "source": "text-parse",
                })
    
    return members


def _clean_name(name: str) -> str:
    """清理姓名格式: 'Jerome H. Powell' → 'Jerome Powell'"""
    name = name.strip()
    # 移除中间名首字母
    name = re.sub(r'\s+[A-Z]\.?\s+', ' ', name)
    # 移除多余空格
    name = re.sub(r'\s+', ' ', name)
    return name


def _clean_role(role: str) -> str:
    """清理角色文本"""
    role = role.lower().strip()
    # 移除括号内容
    role = re.sub(r'\([^)]*\)', '', role)
    role = role.strip()
    
    # 映射到标准角色名
    for key, val in ROLE_MAP.items():
        if key in role:
            return val
    
    return role.title()


def _get_archetype(name: str) -> tuple:
    """获取委员的原型分类"""
    # 精确匹配
    if name in ARCHETYPE_MAP:
        archetype = ARCHETYPE_MAP[name]
    else:
        # 部分匹配
        matched = None
        for known, arch in ARCHETYPE_MAP.items():
            if name.lower() in known.lower() or known.lower() in name.lower():
                matched = arch
                break
        archetype = matched or "Regional Pragmatist"  # 默认务实派
    
    desc = ARCHETYPE_DESCRIPTIONS.get(archetype, "")
    return archetype, desc


def _is_voting_member(role: str, name: str) -> bool:
    """判断是否为有投票权的委员"""
    role_lower = role.lower() if role else ""
    # 所有 Board of Governors 成员都有投票权
    if any(t in role_lower for t in ["chair", "governor", "vice"]):
        return True
    # 地区联储主席轮值投票（简化：NY Fed 永远投票，其他轮流）
    if "president" in role_lower and "new york" in name.lower():
        return True
    return False


def _get_fallback_members() -> List[Dict]:
    """后备成员名单（2026年7月已知配置）"""
    print("  [Board Updater] Using fallback member list (2026-07).")
    return [
        {"name": "Kevin Warsh", "role": "Chair", "archetype": "Central Policymaker",
         "archetype_desc": ARCHETYPE_DESCRIPTIONS["Central Policymaker"], "voting": True, "source": "fallback"},
        {"name": "Philip Jefferson", "role": "Vice Chair", "archetype": "Academic Balancer",
         "archetype_desc": ARCHETYPE_DESCRIPTIONS["Academic Balancer"], "voting": True, "source": "fallback"},
        {"name": "Michelle Bowman", "role": "Vice Chair Supervision", "archetype": "Regional Pragmatist",
         "archetype_desc": ARCHETYPE_DESCRIPTIONS["Regional Pragmatist"], "voting": True, "source": "fallback"},
        {"name": "Michael Barr", "role": "Governor", "archetype": "Academic Balancer",
         "archetype_desc": ARCHETYPE_DESCRIPTIONS["Academic Balancer"], "voting": True, "source": "fallback"},
        {"name": "Lisa Cook", "role": "Governor", "archetype": "Academic Balancer",
         "archetype_desc": ARCHETYPE_DESCRIPTIONS["Academic Balancer"], "voting": True, "source": "fallback"},
        {"name": "Jerome Powell", "role": "Governor", "archetype": "Central Policymaker",
         "archetype_desc": ARCHETYPE_DESCRIPTIONS["Central Policymaker"], "voting": True, "source": "fallback"},
        {"name": "Christopher Waller", "role": "Governor", "archetype": "Central Policymaker",
         "archetype_desc": ARCHETYPE_DESCRIPTIONS["Central Policymaker"], "voting": True, "source": "fallback"},
    ]


# ─── 作为独立脚本运行 ──────────────────────────────────
if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("  FedSight AI - Board Members Auto-Updater")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print()
    
    members = fetch_board_members()
    
    print(f"\n  Total: {len(members)} members")
    print(f"  Voting members: {sum(1 for m in members if m['voting'])}")
    
    # 统计原型分布
    from collections import Counter
    arch_count = Counter(m["archetype"] for m in members)
    print(f"\n  Archetype distribution:")
    for arch, count in arch_count.most_common():
        print(f"    {arch}: {count}")
