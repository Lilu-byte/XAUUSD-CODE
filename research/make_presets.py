#!/usr/bin/env python3
"""Generate MQL5/Presets/*.set from the EA's own input list, so presets always match the code."""
import os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EA = os.path.join(ROOT, "src", "XAU_Sniper_EA.mq5")
PLAT = os.path.join(ROOT, "src", "XAU_Platform.mqh")
OUT = os.path.join(ROOT, "MQL5", "Presets")

def enum_values():
    vals = {"PERIOD_CURRENT": "0"}
    for src in (PLAT, EA):
        for m in re.finditer(r'^\s*(XAU_\w+)\s*=\s*(-?\d+)', open(src).read(), re.M):
            vals[m.group(1)] = m.group(2)
    return vals

def ea_inputs():
    ev = enum_values()
    items = []
    for line in open(EA):
        m = re.match(r'\s*input\s+(?!group)(\w+)\s+(\w+)\s*=\s*([^;]+);', line)
        if not m:
            continue
        name, val = m.group(2), m.group(3).strip()
        val = ev.get(val, val)
        if val.startswith('"'):
            val = val.strip('"')
        items.append((name, val))
    return items

PRESETS = {
    "XAU_Sniper_Balanced": ("Default. Trades the strategy that passed the Strategy Lab (>= 60% wins with profit, walk-forward). 1% risk, 3% daily / 6% weekly stop, 15% drawdown kill-switch.", {}),
    "XAU_Sniper_Conservative": ("Capital preservation: 0.5% risk, tighter limits, and the lab must see 65% winning trades.",
        {"InpRiskPct": "0.5", "InpDailyLossPct": "2.0", "InpWeeklyLossPct": "4.0", "InpMaxDDPct": "10.0", "InpWinTarget": "65.0", "InpMaxTradesPerDay": "4"}),
    "XAU_Sniper_HighWin": ("Highest share of winners: the lab must see 65% wins and every trade uses the High-hit exit (70% closed at 0.5R). Smaller average win; judge it by profit, not win-rate alone.",
        {"InpWinTarget": "65.0", "InpExit": "1"}),
    "XAU_Sniper_Growth": ("Faster compounding: 2% risk. Only after the Balanced set has passed your own tests.",
        {"InpRiskPct": "2.0", "InpDailyLossPct": "4.0", "InpWeeklyLossPct": "8.0", "InpMaxDDPct": "20.0"}),
    "XAU_Sniper_Aggressive": ("HIGH RISK: 4% per trade, the closest to a 'double it' attempt. Expect large drawdowns; read docs/RISK_MATH.md first. Demo only until proven.",
        {"InpRiskPct": "4.0", "InpDailyLossPct": "6.0", "InpWeeklyLossPct": "12.0", "InpMaxDDPct": "30.0"}),
    "XAU_Sniper_DemoTurbo": ("DEMO WATCHING (free run): trades all day (no session filter), several positions, protections only warn, and trades the closest strategy even when none passed the lab (demo accounts only). Many more trades, lower quality, NOT a preview of a real account.",
        {"InpDemoMode": "1", "InpSessionFilter": "false", "InpMaxTradesPerDay": "50", "InpCooldownBars": "0", "InpDemoMaxPositions": "5", "InpDemoUnproven": "true", "InpWinTarget": "55.0"}),
    "XAU_Sniper_GoldORB": ("The GOLD_ORB opening-range breakout on its own; the lab still chooses its best exit. Attach to an XAUUSD H1 chart.",
        {"InpStrategy": "1", "InpOrbSolo": "true"}),
}

def main():
    items = ea_inputs()
    names = {n for n, _ in items}
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".set"):
            os.remove(os.path.join(OUT, f))
    for pname, (desc, over) in PRESETS.items():
        unknown = set(over) - names
        if unknown:
            raise SystemExit("%s: unknown inputs %s" % (pname, unknown))
        lines = ["; " + pname, "; " + desc, "; Load via the EA inputs dialog: Load. Symbol XAUUSD (M15 or H1)."]
        for n, v in items:
            lines.append("%s=%s" % (n, over.get(n, v)))
        with open(os.path.join(OUT, pname + ".set"), "w", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        print("wrote", pname + ".set", "(%d inputs)" % len(items))

main()
