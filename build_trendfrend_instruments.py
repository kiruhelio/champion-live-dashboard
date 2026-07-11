import csv, json, re
from pathlib import Path
from collections import defaultdict

ROOT = Path("/home/ubuntu/.hermes/bots/champion_live_bot/public_report")
DATA = ROOT / "data/baseline_v2026_07"
TRADES = Path("/tmp/grid_3m_1h/out/best_candidate/best_candidate_trades.csv")

def num(x):
    m = re.search(r"-?\d+(?:\.\d+)?", str(x or "").replace(",", ""))
    return float(m.group()) if m else 0.0

summary = json.loads((DATA / "summary.json").read_text())
monthly = json.loads((DATA / "monthly.json").read_text())

with TRADES.open(newline="", encoding="utf-8-sig") as f:
    trades = list(csv.DictReader(f))

sym = defaultdict(lambda: {"raw": 0.0, "trades": 0, "wins": 0, "losses": 0})
month_sym = defaultdict(lambda: {"raw": 0.0, "trades": 0, "wins": 0, "losses": 0})

for r in trades:
    symbol = str(r.get("symbol", "")).upper().replace("USDT", "")
    if symbol not in ("SOL", "NEAR"):
        continue

    month = str(r.get("month", "")).strip()
    if not re.match(r"20\d\d-\d\d", month):
        for c in ["exit_dt", "exit_time", "close_time", "entry_dt", "timestamp", "time", "date"]:
            v = str(r.get(c, ""))
            if re.match(r"20\d\d-\d\d", v):
                month = v[:7]
                break
    if not re.match(r"20\d\d-\d\d", month):
        continue

    pnl = num(r.get("pnl"))
    if pnl == 0:
        pnl = num(r.get("pnl_pct"))

    sym[symbol]["raw"] += pnl
    sym[symbol]["trades"] += 1
    sym[symbol]["wins"] += int(pnl > 0)
    sym[symbol]["losses"] += int(pnl < 0)

    month_sym[(month, symbol)]["raw"] += pnl
    month_sym[(month, symbol)]["trades"] += 1
    month_sym[(month, symbol)]["wins"] += int(pnl > 0)
    month_sym[(month, symbol)]["losses"] += int(pnl < 0)

total_return = float(summary.get("total_return_pct_summary", 0))
raw_total = sum(v["raw"] for v in sym.values()) or 1.0

instrument_summary = []
for symbol in ("SOL", "NEAR"):
    x = sym[symbol]
    contribution = total_return * x["raw"] / raw_total
    instrument_summary.append({
        "symbol": symbol,
        "trades": x["trades"],
        "wins": x["wins"],
        "losses": x["losses"],
        "win_rate": round(x["wins"] / x["trades"] * 100, 2) if x["trades"] else 0,
        "contribution_pct": round(contribution, 2),
        "share_of_return_pct": round(contribution / total_return * 100, 2) if total_return else 0,
    })

monthly_contribution = []
for row in monthly:
    month = row["month"]
    raw_m = sum(month_sym[(month, s)]["raw"] for s in ("SOL", "NEAR")) or 0.0

    out = {
        "month": month,
        "total_return_pct": row["return_pct"],
        "symbols": {}
    }

    for symbol in ("SOL", "NEAR"):
        x = month_sym[(month, symbol)]
        contrib = row["return_pct"] * x["raw"] / raw_m if raw_m else 0.0
        out["symbols"][symbol] = {
            "contribution_pct": round(contrib, 2),
            "trades": x["trades"],
            "wins": x["wins"],
            "losses": x["losses"],
        }

    monthly_contribution.append(out)

(DATA / "instrument_summary.json").write_text(json.dumps(instrument_summary, ensure_ascii=False, indent=2))
(DATA / "instrument_monthly_contribution.json").write_text(json.dumps(monthly_contribution, ensure_ascii=False, indent=2))

print("instrument_summary:")
print(json.dumps(instrument_summary, ensure_ascii=False, indent=2))
