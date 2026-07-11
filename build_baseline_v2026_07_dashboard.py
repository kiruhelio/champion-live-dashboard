import csv, json, re
from pathlib import Path
from collections import defaultdict, Counter

OUT = Path("/tmp/grid_3m_1h/out/best_candidate")
REPORT = Path("/home/ubuntu/.hermes/bots/champion_live_bot/public_report")
DATA = REPORT / "data/baseline_v2026_07"
DATA.mkdir(parents=True, exist_ok=True)

MONTHLY_MD = OUT / "monthly_compounded_performance_report.md"
SUMMARY_CSV = OUT / "best_candidate_summary.csv"
TRADES_CSV = OUT / "best_candidate_trades.csv"
FINAL_TXT = OUT / "best_candidate_final_report.txt"

for p in [MONTHLY_MD, SUMMARY_CSV, TRADES_CSV]:
    if not p.exists():
        raise SystemExit(f"Missing required source: {p}")

def num(x):
    try:
        return float(str(x).replace(",", "").replace("$", "").replace("%", "").strip())
    except Exception:
        return 0.0

def boolish(x):
    return str(x).strip().lower() in {"1", "true", "yes", "y"}

# 1) monthly_compounded_performance_report.md
monthly = []
lines = MONTHLY_MD.read_text(encoding="utf-8", errors="ignore").splitlines()

for line in lines:
    line = line.strip()
    if not line.startswith("|"):
        continue
    if "Month" in line and "Return" in line:
        continue
    if re.match(r"^\|\s*-+", line):
        continue

    parts = [p.strip() for p in line.strip("|").split("|")]
    if len(parts) < 7:
        continue

    month = parts[0]
    if not re.match(r"20\d\d-\d\d", month):
        continue

    start = num(parts[1])
    ret = num(parts[2])
    pnl = num(parts[3])
    end = num(parts[4])
    trades = int(num(parts[5]))
    wr = num(parts[6])

    monthly.append({
        "month": month,
        "start": round(start, 2),
        "return_pct": round(ret, 2),
        "pnl": round(pnl, 2),
        "end": round(end, 2),
        "trades": trades,
        "win_rate": round(wr, 2),
    })

if not monthly:
    raise SystemExit("No monthly rows parsed from monthly_compounded_performance_report.md")

# 2) summary csv
with SUMMARY_CSV.open(newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise SystemExit("summary csv empty")

summary_row = rows[0]
summary_keys = {k.lower(): k for k in summary_row.keys()}

def get_summary(key):
    k = summary_keys.get(key.lower())
    return summary_row.get(k, "") if k else ""

total_return_pct = num(get_summary("total_return_pct"))
win_rate_pct = num(get_summary("win_rate_pct"))
profit_factor = num(get_summary("profit_factor"))
max_dd_pct = num(get_summary("max_dd_pct"))
total_trades = int(num(get_summary("total_trades")))

total_months = len(monthly)
positive_months = sum(1 for r in monthly if r["pnl"] > 0)
negative_months = sum(1 for r in monthly if r["pnl"] < 0)
avg_monthly_return = sum(r["return_pct"] for r in monthly) / total_months
avg_trades_per_month = sum(r["trades"] for r in monthly) / total_months
best_month = max(monthly, key=lambda r: r["pnl"])
worst_month = min(monthly, key=lambda r: r["pnl"])

# 3) trades csv
with TRADES_CSV.open(newline="", encoding="utf-8-sig") as f:
    trades = list(csv.DictReader(f))

if not trades:
    raise SystemExit("trades csv empty")

symbol_month = defaultdict(lambda: {"pnl": 0.0, "trades": 0, "wins": 0})
exit_counter = Counter()
tp_count = 0
sl_count = 0
reverse_count = 0
tp2_count = 0

for r in trades:
    month = str(r.get("month", "")).strip()
    if not month:
        for c in ["exit_dt", "exit_time", "close_time", "entry_dt", "timestamp", "time", "date"]:
            if c in r and re.match(r"20\d\d-\d\d", str(r.get(c, ""))):
                month = str(r.get(c))[:7]
                break
    if not month:
        month = "unknown"

    symbol = str(r.get("symbol", "UNKNOWN")).upper()
    pnl = num(r.get("pnl"))
    exit_type = str(r.get("exit_type", "")).upper().strip()

    key = (month, symbol)
    symbol_month[key]["pnl"] += pnl
    symbol_month[key]["trades"] += 1
    if pnl > 0:
        symbol_month[key]["wins"] += 1

    if exit_type:
        exit_counter[exit_type] += 1

    # Criteria fixed by user: TP = exit_type == TP1 OR hit_tp1 == true. Stops = exit_type == SL.
    if exit_type == "TP1" or boolish(r.get("hit_tp1")):
        tp_count += 1
    if exit_type == "SL":
        sl_count += 1
    if "REVERSE" in exit_type:
        reverse_count += 1
    if boolish(r.get("hit_tp2")) or exit_type == "TP2":
        tp2_count += 1

instrument_monthly = []
months = sorted({m for m, _ in symbol_month if m != "unknown"})
symbols = ["SOLUSDT", "NEARUSDT", "LINKUSDT"]

for m in months:
    row = {"month": m, "symbols": {}}
    for s in symbols:
        x = symbol_month.get((m, s), {"pnl": 0.0, "trades": 0, "wins": 0})
        row["symbols"][s.replace("USDT", "")] = {
            "pnl": round(x["pnl"], 2),
            "return_pct_of_1000": round(x["pnl"] / 1000.0 * 100.0, 2),
            "trades": x["trades"],
            "win_rate": round(x["wins"] / x["trades"] * 100, 1) if x["trades"] else 0,
        }
    instrument_monthly.append(row)

symbol_summary = []
for s in symbols:
    total_pnl = sum(v["pnl"] for (m, sym), v in symbol_month.items() if sym == s)
    total_n = sum(v["trades"] for (m, sym), v in symbol_month.items() if sym == s)
    wins = sum(v["wins"] for (m, sym), v in symbol_month.items() if sym == s)
    symbol_summary.append({
        "symbol": s.replace("USDT", ""),
        "pnl": round(total_pnl, 2),
        "return_pct_of_1000": round(total_pnl / 1000.0 * 100.0, 2),
        "trades": total_n,
        "win_rate": round(wins / total_n * 100, 1) if total_n else 0,
    })

# equity from monthly standard table
equity = [{"month": r["month"], "equity": r["end"]} for r in monthly]

peak = monthly[0]["start"] if monthly else 1000.0
drawdown = []
for r in monthly:
    peak = max(peak, r["end"])
    dd = (peak - r["end"]) / peak * 100 if peak else 0
    drawdown.append({"month": r["month"], "drawdown_pct": round(dd, 2)})

dashboard_summary = {
    "title": "Absolute Champion Live Baseline v2026-07",
    "mode": "SOL70 / NEAR30 · 3m / 1h · Monthly Fixed-Return Compounding",
    "portfolio": {"SOL": 70, "NEAR": 30, "LINK": 0},
    "timeframes": {"entry": "3m", "trend_filter": "1h"},
    "total_return_pct_summary": round(total_return_pct, 2),
    "total_return_pct_monthly_fixed_return_compounding": round((monthly[-1]["end"] / monthly[0]["start"] - 1) * 100, 2),
    "final_equity": round(monthly[-1]["end"], 2),
    "start_equity": round(monthly[0]["start"], 2),
    "profit_factor": round(profit_factor, 4),
    "win_rate": round(win_rate_pct, 2),
    "max_drawdown_pct": round(max_dd_pct, 2),
    "total_trades": total_trades,
    "total_months": total_months,
    "positive_months": positive_months,
    "negative_months": negative_months,
    "avg_monthly_return": round(avg_monthly_return, 2),
    "avg_trades_per_month": round(avg_trades_per_month, 1),
    "best_month": best_month,
    "worst_month": worst_month,
    "tp_count": tp_count,
    "tp2_count": tp2_count,
    "sl_count": sl_count,
    "reverse_count": reverse_count,
    "exit_types": dict(exit_counter),
    "sources": {
        "monthly_report": str(MONTHLY_MD),
        "summary_csv": str(SUMMARY_CSV),
        "trades_csv": str(TRADES_CSV),
        "final_report": str(FINAL_TXT),
    }
}

if total_trades <= 0 or total_months < 12 or profit_factor <= 0:
    raise SystemExit("Invalid dashboard data; refusing publish")

(DATA / "summary.json").write_text(json.dumps(dashboard_summary, ensure_ascii=False, indent=2))
(DATA / "monthly.json").write_text(json.dumps(monthly, ensure_ascii=False, indent=2))
(DATA / "equity.json").write_text(json.dumps(equity, ensure_ascii=False, indent=2))
(DATA / "drawdown.json").write_text(json.dumps(drawdown, ensure_ascii=False, indent=2))
(DATA / "instrument_monthly.json").write_text(json.dumps(instrument_monthly, ensure_ascii=False, indent=2))
(DATA / "symbol_summary.json").write_text(json.dumps(symbol_summary, ensure_ascii=False, indent=2))

print("BUILT BASELINE DASHBOARD DATA OK")
print(json.dumps(dashboard_summary, ensure_ascii=False, indent=2))
