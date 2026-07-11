import csv, json, re, math
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/home/ubuntu/.hermes/bots/champion_live_bot/public_report")
DATA = ROOT / "data/baseline_v2026_07"
SRC = Path("/tmp/grid_3m_1h/out/best_candidate")
TRADES = SRC / "best_candidate_trades.csv"

def num(x):
    m = re.search(r"-?\d+(?:\.\d+)?", str(x or "").replace(",", ""))
    return float(m.group()) if m else None

def parse_time(x):
    s = str(x or "").strip()
    if not s:
        return None
    v = num(s)
    if v and v > 1000000000:
        if v > 1000000000000:
            v /= 1000
        return datetime.fromtimestamp(v, tz=timezone.utc)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt).replace(tzinfo=timezone.utc)
        except:
            pass
    return None

summary = json.loads((DATA / "summary.json").read_text())
monthly = json.loads((DATA / "monthly.json").read_text())
inst = json.loads((DATA / "instrument_summary.json").read_text())

# Убираем LINK из данных
inst = [x for x in inst if x.get("symbol") in ("SOL", "NEAR")]
(DATA / "instrument_summary.json").write_text(json.dumps(inst, ensure_ascii=False, indent=2))

im = json.loads((DATA / "instrument_monthly.json").read_text())
for r in im:
    if "symbols" in r:
        r["symbols"] = {k:v for k,v in r["symbols"].items() if k in ("SOL","NEAR")}
(DATA / "instrument_monthly.json").write_text(json.dumps(im, ensure_ascii=False, indent=2))

# Метрики по сделкам
trades = []
if TRADES.exists():
    with TRADES.open(newline="", encoding="utf-8-sig") as f:
        trades = list(csv.DictReader(f))

pnl_values = []
risk_values = []
hold_hours = []
wins_losses = []

risk_cols = ["risk_pct", "risk_percent", "risk", "risk_fraction"]
entry_cols = ["entry_time", "entry_dt", "entry_ts", "open_time", "open_ts"]
exit_cols = ["exit_time", "exit_dt", "exit_ts", "close_time", "close_ts"]

for r in trades:
    pnl = num(r.get("pnl"))
    if pnl is None:
        pnl = num(r.get("pnl_pct"))
    if pnl is not None:
        pnl_values.append(pnl)
        wins_losses.append(1 if pnl > 0 else -1 if pnl < 0 else 0)

    for c in risk_cols:
        if c in r:
            rv = num(r.get(c))
            if rv is not None:
                risk_values.append(abs(rv))
            break

    et = next((parse_time(r.get(c)) for c in entry_cols if c in r and parse_time(r.get(c))), None)
    xt = next((parse_time(r.get(c)) for c in exit_cols if c in r and parse_time(r.get(c))), None)
    if et and xt and xt > et:
        hold_hours.append((xt - et).total_seconds() / 3600)

gross_win = sum(x for x in pnl_values if x > 0)
gross_loss = abs(sum(x for x in pnl_values if x < 0))
avg_win = gross_win / max(1, sum(1 for x in pnl_values if x > 0))
avg_loss = gross_loss / max(1, sum(1 for x in pnl_values if x < 0))
avg_rr = avg_win / avg_loss if avg_loss else None

max_win_streak = max_loss_streak = cur_win = cur_loss = 0
for x in wins_losses:
    if x > 0:
        cur_win += 1
        cur_loss = 0
    elif x < 0:
        cur_loss += 1
        cur_win = 0
    else:
        cur_win = cur_loss = 0
    max_win_streak = max(max_win_streak, cur_win)
    max_loss_streak = max(max_loss_streak, cur_loss)

total_return = float(summary.get("total_return_pct_summary", 0))
max_dd = float(summary.get("max_drawdown_pct", 0))
total_trades = int(summary.get("total_trades", 0))
months = int(summary.get("total_months", len(monthly)))

summary["avg_trade_return_pct"] = round(total_return / total_trades, 3) if total_trades else None
summary["recovery_factor"] = round(total_return / max_dd, 2) if max_dd else None
summary["cagr_pct"] = round(((1 + total_return / 100) ** (12 / months) - 1) * 100, 2) if months else None
summary["avg_risk_per_trade_pct"] = round(sum(risk_values) / len(risk_values), 3) if risk_values else None
summary["avg_risk_reward"] = round(avg_rr, 2) if avg_rr else None
summary["max_loss_streak"] = max_loss_streak
summary["max_win_streak"] = max_win_streak
summary["avg_hold_hours"] = round(sum(hold_hours) / len(hold_hours), 2) if hold_hours else None

(DATA / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print("summary updated")
