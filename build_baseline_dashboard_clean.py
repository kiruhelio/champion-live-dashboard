import csv, json, re
from pathlib import Path
from collections import defaultdict, Counter

SRC = Path("/tmp/grid_3m_1h/out/best_candidate")
OUT = Path("/home/ubuntu/.hermes/bots/champion_live_bot/public_report/data/baseline_v2026_07")
OUT.mkdir(parents=True, exist_ok=True)

MONTHLY = SRC / "monthly_compounded_performance_report.md"
SUMMARY = SRC / "best_candidate_summary.csv"
TRADES = SRC / "best_candidate_trades.csv"

REQUIRED = [MONTHLY, SUMMARY, TRADES]
for p in REQUIRED:
    if not p.exists():
        raise SystemExit(f"ERROR missing source: {p}")

def n(x):
    s = str(x or "").replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else 0.0

def yes(x):
    return str(x).strip().lower() in {"1", "true", "yes", "y"}

monthly = []
for line in MONTHLY.read_text(encoding="utf-8", errors="ignore").splitlines():
    line = line.strip()
    m = re.match(
        r"^(20\d\d-\d\d)\s*\|\s*Start=([^|]+)\|\s*Return=([^|]+)\|\s*PnL=([^|]+)\|\s*End=([^|]+)\|\s*Trades=([^|]+)\|\s*WR=([^|]+)",
        line
    )
    if not m:
        continue

    month, start, ret, pnl, end, trades, wr = m.groups()
    monthly.append({
        "month": month,
        "start": round(n(start), 2),
        "return_pct": round(n(ret), 2),
        "pnl": round(n(pnl), 2),
        "end": round(n(end), 2),
        "trades": int(n(trades)),
        "win_rate": round(n(wr), 2),
    })

if len(monthly) < 12:
    raise SystemExit(f"ERROR monthly rows parsed: {len(monthly)}")

with SUMMARY.open(newline="", encoding="utf-8-sig") as f:
    summary_row = list(csv.DictReader(f))[0]
summary_row = {k.lower(): v for k, v in summary_row.items()}

with TRADES.open(newline="", encoding="utf-8-sig") as f:
    trades = list(csv.DictReader(f))

if not trades:
    raise SystemExit("ERROR trades empty")

symbols = ["SOL", "NEAR", "LINK"]
instrument_total = defaultdict(lambda: {"pnl": 0.0, "trades": 0, "wins": 0})
instrument_month = defaultdict(lambda: {"pnl": 0.0, "trades": 0, "wins": 0})
exit_types = Counter()

tp1 = tp2 = sl = reverse = 0

for r in trades:
    symbol = str(r.get("symbol", "UNKNOWN")).upper().replace("USDT", "")
    month = str(r.get("month", "")).strip()

    if not re.match(r"20\d\d-\d\d", month):
        for c in ["exit_dt", "exit_time", "close_time", "entry_dt", "timestamp", "time", "date"]:
            v = str(r.get(c, ""))
            if re.match(r"20\d\d-\d\d", v):
                month = v[:7]
                break

    if not re.match(r"20\d\d-\d\d", month):
        month = "unknown"

    pnl = n(r.get("pnl"))
    et = str(r.get("exit_type", "")).upper().strip()

    instrument_total[symbol]["pnl"] += pnl
    instrument_total[symbol]["trades"] += 1
    instrument_total[symbol]["wins"] += int(pnl > 0)

    instrument_month[(month, symbol)]["pnl"] += pnl
    instrument_month[(month, symbol)]["trades"] += 1
    instrument_month[(month, symbol)]["wins"] += int(pnl > 0)

    if et:
        exit_types[et] += 1
    if et == "TP1" or yes(r.get("hit_tp1")):
        tp1 += 1
    if et == "TP2" or yes(r.get("hit_tp2")):
        tp2 += 1
    if et == "SL":
        sl += 1
    if "REVERSE" in et:
        reverse += 1

equity = [{"month": r["month"], "equity": r["end"]} for r in monthly]

drawdown = []
peak = monthly[0]["start"]
for r in monthly:
    peak = max(peak, r["end"])
    dd = (peak - r["end"]) / peak * 100 if peak else 0
    drawdown.append({"month": r["month"], "drawdown_pct": round(dd, 2)})

instrument_monthly = []
for r in monthly:
    m = r["month"]
    row = {"month": m, "symbols": {}}
    for s in symbols:
        x = instrument_month.get((m, s), {"pnl": 0.0, "trades": 0, "wins": 0})
        row["symbols"][s] = {
            "pnl": round(x["pnl"], 2),
            "return_pct_of_1000": round(x["pnl"] / 1000 * 100, 2),
            "trades": x["trades"],
            "win_rate": round(x["wins"] / x["trades"] * 100, 1) if x["trades"] else 0,
        }
    instrument_monthly.append(row)

instrument_summary = []
for s in symbols:
    x = instrument_total.get(s, {"pnl": 0.0, "trades": 0, "wins": 0})
    instrument_summary.append({
        "symbol": s,
        "pnl": round(x["pnl"], 2),
        "return_pct_of_1000": round(x["pnl"] / 1000 * 100, 2),
        "trades": x["trades"],
        "win_rate": round(x["wins"] / x["trades"] * 100, 1) if x["trades"] else 0,
    })

best_month = max(monthly, key=lambda x: x["pnl"])
worst_month = min(monthly, key=lambda x: x["pnl"])

summary = {
    "title": "Absolute Champion Live Baseline v2026-07",
    "mode": "SOL70 / NEAR30 · 3m / 1h · Monthly Fixed-Return Compounding",
    "portfolio": {"SOL": 70, "NEAR": 30, "LINK": 0},
    "start_equity": monthly[0]["start"],
    "final_equity": monthly[-1]["end"],
    "total_return_pct_summary": round(n(summary_row.get("total_return_pct")), 2),
    "total_return_pct_monthly_fixed_return_compounding": round((monthly[-1]["end"] / monthly[0]["start"] - 1) * 100, 2),
    "profit_factor": round(n(summary_row.get("profit_factor")), 4),
    "win_rate": round(n(summary_row.get("win_rate_pct")), 2),
    "max_drawdown_pct": round(n(summary_row.get("max_dd_pct")), 2),
    "total_trades": int(n(summary_row.get("total_trades"))),
    "total_months": len(monthly),
    "positive_months": sum(1 for x in monthly if x["pnl"] > 0),
    "negative_months": sum(1 for x in monthly if x["pnl"] < 0),
    "avg_monthly_return": round(sum(x["return_pct"] for x in monthly) / len(monthly), 2),
    "avg_trades_per_month": round(sum(x["trades"] for x in monthly) / len(monthly), 1),
    "best_month": best_month,
    "worst_month": worst_month,
    "tp1_count": tp1,
    "tp2_count": tp2,
    "sl_count": sl,
    "reverse_count": reverse,
    "exit_types": dict(exit_types),
    "sources": {
        "monthly_report": str(MONTHLY),
        "summary_csv": str(SUMMARY),
        "trades_csv": str(TRADES),
    }
}

payloads = {
    "summary.json": summary,
    "monthly.json": monthly,
    "equity.json": equity,
    "drawdown.json": drawdown,
    "instrument_monthly.json": instrument_monthly,
    "instrument_summary.json": instrument_summary,
    "exits.json": {
        "tp1": tp1,
        "tp2": tp2,
        "sl": sl,
        "reverse": reverse,
        "exit_types": dict(exit_types),
    }
}

for name, data in payloads.items():
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2))

for name in payloads:
    p = OUT / name
    if not p.exists() or p.stat().st_size == 0:
        raise SystemExit(f"ERROR failed to create {p}")

print("BASELINE DATA BUILT OK")
print(json.dumps(summary, ensure_ascii=False, indent=2))
