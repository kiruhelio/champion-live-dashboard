import csv, json
from pathlib import Path
from collections import defaultdict

src = Path("/home/ubuntu/.hermes/bots/research_near_only_baseline_20260709_181451/out_dynamic_risk_after_loss")
out = Path("/home/ubuntu/.hermes/bots/champion_live_bot/public_report/data/dynamic-risk")
out.mkdir(parents=True, exist_ok=True)

# Copy CSVs
for name in ["trades.csv","monthly.csv","yearly.csv"]:
    (src/name).replace(out/name)

# Summary CSV -> JSON
s = {}
with (src/"summary.csv").open(encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        k, v = row["metric"], row["value"]
        try:
            s[k] = float(v) if "." in v else int(v)
        except:
            s[k] = v
(out/"summary.json").write_text(json.dumps(s, indent=2), encoding="utf-8")

# Generate instrument_summary from trades
inst = defaultdict(lambda: {"trades":0,"wins":0,"losses":0,"pnl_pct":0.0,"return_pct":0.0,"best":"","worst":"","share_of_return_pct":0.0})
for r in csv.DictReader((out/"trades.csv").open(encoding="utf-8-sig")):
    sym = r["symbol"].replace("USDT","")
    pnl = float(r["pnl"])
    inst[sym]["trades"] += 1
    inst[sym]["pnl_pct"] += pnl
    if pnl >= 0:
        inst[sym]["wins"] += 1
    else:
        inst[sym]["losses"] += 1

total_ret = sum(v["pnl_pct"] for v in inst.values())
for sym, v in inst.items():
    v["return_pct"] = v["pnl_pct"]
    v["share_of_return_pct"] = (v["pnl_pct"]/total_ret*100) if total_ret else 0

with (out/"instrument_summary.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["symbol","return_pct","share_of_return_pct","trades","wins","losses","share_of_volume_pct"])
    for sym, v in inst.items():
        w.writerow([sym, v["return_pct"], v["share_of_return_pct"], v["trades"], v["wins"], v["losses"], ""])

# Generate monthly_instruments from trades + monthly
month_inst = defaultdict(lambda: defaultdict(float))
for r in csv.DictReader((out/"trades.csv").open(encoding="utf-8-sig")):
    sym = r["symbol"].replace("USDT","")
    month_inst[r["month"]][sym] += float(r["pnl"])

with (out/"monthly_instruments.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["month","symbol","return_pct","trades","wins","losses"])
    for month in sorted(month_inst):
        for sym in ["SOL","NEAR"]:
            v = month_inst[month][sym]
            w.writerow([month, sym, v, "", "", ""])

# Generate equity_curve_monthly from monthly
with (out/"equity_curve_monthly.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["month","end_eq"])
    eq = 1000.0
    for r in csv.DictReader((out/"monthly.csv").open(encoding="utf-8-sig")):
        month = r["month"]
        eq = eq * (1 + float(r["return_pct"])/100)
        w.writerow([month, f"{eq:.6f}"])

# Generate drawdown_monthly from equity curve
eqs = []
with (out/"equity_curve_monthly.csv").open(encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        eqs.append((r["month"], float(r["end_eq"])))

with (out/"drawdown_monthly.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["month","drawdown_pct"])
    peak = eqs[0][1] if eqs else 1000.0
    for month, eq in eqs:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        w.writerow([month, f"{-dd:.4f}"])

print("done:", out)
for p in out.iterdir():
    print(" ", p.name)
