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

# Since round 14 the EA's defaults collect data on a demo (free run, no loss limits). The presets meant for a real
# account carry the account protection explicitly.
LIVE = {"InpDemoMode": "0", "InpDemoUnproven": "false", "InpDailyLossPct": "3.0", "InpWeeklyLossPct": "6.0", "InpMaxDDPct": "15.0",
        "InpMaxConsecLosses": "3", "InpMaxTradesPerDay": "6", "InpCooldownBars": "2"}

def live(over):
    d = dict(LIVE)
    d.update(over)
    return d

PRESETS = {
    "XAU_Sniper_Balanced": ("For a real account (or a demo rehearsal of one): trades only what passed the Strategy Lab, 1% risk, 3% daily / 6% weekly stop, 15% drawdown kill-switch, pause after 3 losses in a row.", live({})),
    # one data-collection copy per chart (own magic numbers, so the copies never block each other)
    "XAU_Sniper_DataCollect_M5": ("DEMO DATA COLLECTION on an XAUUSD M5 chart (about 4 trades a day in the replay): every signal, all day, no loss limits, journal on. Run with the _M15 and _H1 sets on two more charts.",
        {"InpDemoMode": "1", "InpDemoUnproven": "true", "InpSessionFilter": "false", "InpDemoMaxPositions": "5", "InpJournal": "true", "InpMagic": "20262005", "InpComment": "XAUD5"}),
    "XAU_Sniper_DataCollect_M15": ("DEMO DATA COLLECTION on an XAUUSD M15 chart (about 1 trade a day in the replay): every signal, all day, no loss limits, journal on.",
        {"InpDemoMode": "1", "InpDemoUnproven": "true", "InpSessionFilter": "false", "InpDemoMaxPositions": "5", "InpJournal": "true", "InpMagic": "20262015", "InpComment": "XAUD15"}),
    "XAU_Sniper_DataCollect_H1": ("DEMO DATA COLLECTION on an XAUUSD H1 chart: TREND mode with the daily trend filter OFF, so it also trades (both ways) while gold is below its 200-day mean; about 0.6 trades a day in the replay, weaker than with the filter (+0.03R vs +0.12R). Journal on.",
        {"InpDemoMode": "1", "InpDemoUnproven": "true", "InpSessionFilter": "false", "InpDemoMaxPositions": "5", "InpJournal": "true", "InpDailyTrend": "0", "InpMagic": "20262060", "InpComment": "XAUD60"}),
    "XAU_Sniper_DataCollect": ("DEMO DATA COLLECTION: trades every signal the strategies find (proven or not), all day, up to 5 positions, no loss limits, and writes every trade and skipped signal to MQL5/Files/XAU_Export/XAU_Sniper_journal_<symbol>.csv. Send that file for analysis. Not a preview of a real account.",
        {"InpDemoMode": "1", "InpDemoUnproven": "true", "InpSessionFilter": "false", "InpDemoMaxPositions": "5", "InpJournal": "true"}),
    "XAU_Sniper_Conservative": ("Capital preservation: 0.5% risk, tighter limits, and the lab must see 65% winning trades.",
        live({"InpRiskPct": "0.5", "InpDailyLossPct": "2.0", "InpWeeklyLossPct": "4.0", "InpMaxDDPct": "10.0", "InpWinTarget": "65.0", "InpMaxTradesPerDay": "4"})),
    "XAU_Sniper_HighWin": ("Highest share of winners: the lab must see 65% wins and every trade uses the High-hit exit (70% closed at 0.5R). Smaller average win; judge it by profit, not win-rate alone.",
        live({"InpWinTarget": "65.0", "InpExit": "1"})),
    "XAU_Sniper_Growth": ("Faster compounding: 2% risk. Only after the Balanced set has passed your own tests.",
        live({"InpRiskPct": "2.0", "InpDailyLossPct": "4.0", "InpWeeklyLossPct": "8.0", "InpMaxDDPct": "20.0"})),
    "XAU_Sniper_Aggressive": ("HIGH RISK: 4% per trade, the closest to a 'double it' attempt. Expect large drawdowns; read docs/RISK_MATH.md first. Demo only until proven.",
        live({"InpRiskPct": "4.0", "InpDailyLossPct": "6.0", "InpWeeklyLossPct": "12.0", "InpMaxDDPct": "30.0"})),
    "XAU_Sniper_DemoTurbo": ("DEMO WATCHING (free run): trades all day (no session filter), several positions, protections only warn, and trades the closest strategy even when none passed the lab (demo accounts only). Many more trades, lower quality, NOT a preview of a real account.",
        {"InpDemoMode": "1", "InpSessionFilter": "false", "InpMaxTradesPerDay": "50", "InpCooldownBars": "0", "InpDemoMaxPositions": "5", "InpDemoUnproven": "true", "InpWinTarget": "55.0"}),
    # one EA per chart, three charts at once: more trades from independent daily Labs (different magic numbers)
    "XAU_Sniper_Multi_M15": ("Run together with the Multi_H1 and Multi_H4 sets: attach the EA to an XAUUSD M15 chart with this set. Own magic number, so the three copies never block each other.",
        {"InpMagic": "20261015", "InpComment": "XAUS15"}),
    "XAU_Sniper_Multi_H1": ("Run together with Multi_M15 and Multi_H4: XAUUSD H1 chart. AUTO = TREND mode here: buys only while the daily trend is up, multi-day exits, Lab on about 4 years.",
        {"InpMagic": "20261060", "InpComment": "XAUS60"}),
    "XAU_Sniper_Multi_H4": ("Run together with Multi_M15 and Multi_H1: XAUUSD H4 chart. AUTO = TREND mode here: buys only while the daily trend is up, multi-day exits.",
        {"InpMagic": "20261240", "InpComment": "XAUS240"}),
    "XAU_Sniper_Trend": ("TREND mode on any chart (best on XAUUSD H1): every strategy that passes a 50% Lab target trades, up to 3 positions, multi-day trend-riding exits, H1+ buys only in a daily uptrend. Real-data replay H1 Oct 2020 - Sep 2026 (rising 200-day mean filter): +0.12R per trade over 722 trades, 57% winners, mostly earned in 2024-2025 (a trend follower). Positions are held for days and pay swap.",
        {"InpMode": "1"}),
    "XAU_Sniper_Steady": ("STEADY mode on any chart: one strategy with 60%+ winners (high win-rate, about break-even on real gold).",
        {"InpMode": "0"}),
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
