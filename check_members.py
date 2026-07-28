import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from fed_sim import FOMC_MEMBERS, CHAIR_NAME, CHAIR_DESC

print("=" * 60)
print(f"  FOMC Chair: {CHAIR_NAME}")
print(f"  Scenario: {CHAIR_DESC}")
print("=" * 60)
print(f"\n  Total members: {len(FOMC_MEMBERS)}")
print()
for i, m in enumerate(FOMC_MEMBERS, 1):
    print(f"  {i:2d}. {m['name']:15s} | {m['role']:25s} | {m['archetype']}")
print()
print("  Available scenarios (set FOMC_CHAIR env var):")
print("    bowman, waller, powell_governor, jefferson (default)")
