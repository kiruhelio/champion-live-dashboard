import csv, json, re
from pathlib import Path
from collections import defaultdict

ROOT = Path("/home/ubuntu/.hermes/bots/champion_live_bot")
DATA = ROOT / "public_report/data/portfolio_3m_1h"
DATA.mkdir(parents=True, exist_ok=True)

START = 1000.0

candidates = list(ROOT.glob("out/best_candidate/**/*.csv")) + list(ROOT.glob("**/*3m*1h*.csv")) + list(ROOT.glob("**/*best*candidate*.csv"))
trades_files = [p for p in candidates if "trade" in p.name.lower() and p.is_file()]

print("FOUND TRADE CANDIDATES:")
for p in trades_files:
    print(" -", p)

if not trades_files:
    raise SystemExit("ERROR: no trades CSV found. Need trades CSV for 3m+1h run.")

SRC = trades_files[0]
rows = list(csv.DictReader(open(SRC, newline="", encoding="utf-8-sig")))
if not rows:
    raise SystemExit(f"ERROR: empty CSV: {SRC}")

cols = list(rows[0].keys())
print("USING:", SRC)
print("COLUMNS:", cols)
print("FIRST ROW:", rows[0])

def num(x):
    try:
        return float(str(x or "").replace(",", "").replace("%", "").replace("$", "").strip())
    except:
        return 0.0

def pick(names):
    low = {c.lower(): c for c in cols}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None

sym_col = pick(["symbol","instrument","ticker"])
date_col = pick(["exit_dt","exit_time","close_time","timestamp","time","date","entry_dt"])
pnl_pct_col = pick(["pnl_pct_display","pnl_pct","return_pct","profit_pct"])
pnl_col = pick(["pnl_usdt","pnl","profit","net_pnl"])

if not date_col:
    for c in cols:
        if any(re.search(r"20\d\d[-/]\d\d", str(r.get(c,""))) for r in rows[:50]):
            date_col = c
            break

if not pnl_pct_col and not pnl_col:
    raise SystemExit("ERROR: no PnL column found")

rows.sort(key=lambda r: str(r.get(date_col, "")))

eq = START
peak = START
equity = []
drawdown = []

monthly = defaultdict(lambda: {"profit":0.0,"trades":0,"wins":0,"gp":0.0,"gl":0.0})
yearly = defaultdict(lambda: {"profit":0.0,"trades":0,"wins":0,"gp":0.0,"gl":0.0})
symbols = defaultdict(lambda: {"profit":0.0,"trades":0,"wins":0,"gp":0.0,"gl":0.0})

for r in rows:
    dt = str(r.get(date_col,""))
    month = dt[:7] if re.match(r"20\d\d[-/]\d\d", dt) else "unknown"
    year = month[:4] if month != "unknown" else "unknown"
    sym = str(r.get(sym_col,"UNKNOWN")).upper() if sym_col else "UNKNOWN"

    pnl = START * num(r.get(pnl_pct_col)) / 100.0 if pnl_pct_col else num(r.get(pnl_col))

    eq += pnl
    peak = max(peak, eq)
    dd = (peak - eq) / peak * 100 if peak else 0

    equity.append({"date":dt,"month":month,"equity":round(eq,2)})
    drawdown.append({"date":dt,"month":month,"drawdown_pct":round(dd,2)})

    for b in (monthly[month], yearly[year], symbols[sym]):
        b["profit"] += pnl
        b["trades"] += 1
        if pnl > 0:
            b["wins"] += 1
            b["gp"] += pnl
        elif pnl < 0:
            b["gl"] += abs(pnl)

def pack(mp, key):
    out = []
    for k in sorted(mp):
        if k == "unknown":
            continue
        x = mp[k]
        pf = x["gp"] / x["gl"] if x["gl"] else None
        out.append({
            key:k,
            "return_pct":round(x["profit"]/START*100,2),
            "profit":round(x["profit"],2),
            "trades":x["trades"],
            "win_rate":round(x["wins"]/x["trades"]*100,1) if x["trades"] else 0,
            "pf":round(pf,2) if pf else None,
            "gross_profit":round(x["gp"],2),
            "gross_loss":round(x["gl"],2),
        })
    return out

monthly_rows = pack(monthly, "month")
yearly_rows = pack(yearly, "year")
symbol_rows = pack(symbols, "symbol")

gp = sum(x["gross_profit"] for x in symbol_rows)
gl = sum(x["gross_loss"] for x in symbol_rows)
wins = sum(1 for r in rows if (START*num(r.get(pnl_pct_col))/100.0 if pnl_pct_col else num(r.get(pnl_col))) > 0)

summary = {
    "title":"Absolute Champion 3m + 1h Portfolio",
    "mode":"PORTFOLIO · 3m / 1h · SOL 60 / NEAR 20 / LINK 20 · NO REINVEST",
    "start_capital":START,
    "final_equity":round(eq,2),
    "total_return_pct":round((eq-START)/START*100,2),
    "profit_factor":round(gp/gl,2) if gl else None,
    "win_rate":round(wins/len(rows)*100,1),
    "max_drawdown_pct":round(max(x["drawdown_pct"] for x in drawdown),2),
    "total_trades":len(rows),
    "total_months":len(monthly_rows),
    "positive_months":sum(1 for x in monthly_rows if x["return_pct"] > 0),
    "negative_months":sum(1 for x in monthly_rows if x["return_pct"] < 0),
    "avg_monthly_return":round(sum(x["return_pct"] for x in monthly_rows)/len(monthly_rows),2) if monthly_rows else 0,
    "best_month":max(monthly_rows,key=lambda x:x["return_pct"]) if monthly_rows else None,
    "worst_month":min(monthly_rows,key=lambda x:x["return_pct"]) if monthly_rows else None,
    "portfolio":{"SOL":60,"NEAR":20,"LINK":20},
    "source":str(SRC),
}

if summary["total_trades"] <= 0 or summary["final_equity"] == START or not monthly_rows or not yearly_rows:
    raise SystemExit("ERROR: generated invalid dashboard data")

(DATA/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(DATA/"monthly.json").write_text(json.dumps(monthly_rows,ensure_ascii=False,indent=2))
(DATA/"yearly.json").write_text(json.dumps(yearly_rows,ensure_ascii=False,indent=2))
(DATA/"symbols.json").write_text(json.dumps(symbol_rows,ensure_ascii=False,indent=2))
(DATA/"equity.json").write_text(json.dumps(equity,ensure_ascii=False,indent=2))
(DATA/"drawdown.json").write_text(json.dumps(drawdown,ensure_ascii=False,indent=2))

print("BUILT OK")
print(json.dumps(summary,ensure_ascii=False,indent=2))
