import csv, json, os
from pathlib import Path
from collections import defaultdict

SRC = Path(os.environ["SRC"])
OUT = Path("/home/ubuntu/.hermes/bots/champion_live_bot/public_report/trendfrend")
OUT.mkdir(parents=True, exist_ok=True)

def read_csv(name):
    with (SRC / name).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def num(x):
    return float(str(x or 0).replace("%","").replace(",","").strip() or 0)

def fmt(x, d=2):
    return f"{num(x):,.{d}f}"

def sci(x):
    return f"{num(x):.2e}".replace("e+", " × 10^")

def cls(x):
    return "green" if num(x) >= 0 else "red"

def plus(x):
    return "+" if num(x) >= 0 else ""

s = json.loads((SRC / "summary.json").read_text(encoding="utf-8"))
monthly = read_csv("monthly.csv")
equity = read_csv("equity_curve_monthly.csv")
dd = read_csv("drawdown_monthly.csv")
inst = read_csv("instrument_summary.csv")
mi = read_csv("monthly_instruments.csv")

total_return = num(s.get("total_return_pct"))
max_dd = num(s.get("max_dd_pct") or s.get("max_drawdown_pct"))
pf = num(s.get("profit_factor"))
wr = num(s.get("win_rate_pct") or s.get("win_rate"))
trades = num(s.get("total_trades"))
avg_trade = num(s.get("avg_trade_return_pct"))
avg_hold = num(s.get("avg_hold_hours"))
avg_month = num(s.get("avg_monthly_return_pct") or s.get("avg_monthly_return"))
pos_months = int(num(s.get("positive_months")))
neg_months = int(num(s.get("negative_months")))
avg_trades_month = trades / max(len(monthly), 1)

best = max(monthly, key=lambda r: num(r["return_pct"]))
worst = min(monthly, key=lambda r: num(r["return_pct"]))

def card(label, value, sub="", color=""):
    return f'<div class="card"><div class="label">{label}</div><div class="value {color}">{value}</div><div class="sub">{sub}</div></div>'

def mini(label, value, sub="", color=""):
    return f'<div class="mini"><span class="label">{label}</span><b class="{color}">{value}</b><span class="sub">{sub}</span></div>'

kpis = "".join([
    card("Доходность", sci(total_return)+"%", "Monthly Fixed-Return", "green"),
    card("MaxDD", fmt(max_dd)+"%", "month-to-month", "red"),
    card("Profit Factor", fmt(pf,4), "summary.json", "green"),
    card("Win Rate", fmt(wr)+"%", "summary.json"),
    card("Средняя сделка", plus(avg_trade)+fmt(avg_trade,3)+"%", "avg_trade_return", "green"),
    card("Среднее время", fmt(avg_hold,2)+" ч", "avg_hold_hours"),
    card("Всего сделок", fmt(trades,0), f"{len(monthly)} месяцев"),
    card("Сделок в месяц", fmt(avg_trades_month,1), "средняя активность"),
])

month_summary = "".join([
    mini("Средний месяц", plus(avg_month)+fmt(avg_month)+"%", "avg_monthly_return", "green"),
    mini("Лучший месяц", plus(best["return_pct"])+fmt(best["return_pct"])+"%", best["month"], "green"),
    mini("Худший месяц", plus(worst["return_pct"])+fmt(worst["return_pct"])+"%", worst["month"], "red"),
    mini("Прибыльных месяцев", f"{pos_months} / {len(monthly)}", f"{pos_months/len(monthly)*100:.1f}%", "green"),
    mini("Убыточных месяцев", f"{neg_months} / {len(monthly)}", f"{neg_months/len(monthly)*100:.1f}%", "red"),
])

risk_compare = "".join([
    mini("Risk per Month", "1.00%", "текущий режим", "green"),
    mini("MaxDD 1.0%", "26.04%", "предыдущий риск", "red"),
    mini("MaxDD 1.0%", fmt(max_dd)+"%", "текущий риск", "green"),
    mini("Risk profile", "≈2×", "1.00% monthly", "green"),
    mini("PF", fmt(pf,4), "без ухудшения", "green"),
])

by = defaultdict(lambda: {"vals":[None]*12, "sum":0})
for r in monthly:
    y = r["month"][:4]
    i = int(r["month"][5:7]) - 1
    v = num(r["return_pct"])
    by[y]["vals"][i] = v
    by[y]["sum"] += v

monthly_rows = ""
for y in sorted(by):
    row = f"<tr><td><b>{y}</b></td>"
    for v in by[y]["vals"]:
        row += "<td>—</td>" if v is None else f'<td class="{cls(v)}">{plus(v)}{fmt(v,1)}%</td>'
    row += f'<td class="{cls(by[y]["sum"])}"><b>{plus(by[y]["sum"])}{fmt(by[y]["sum"],1)}%</b></td></tr>'
    monthly_rows += row

cy = defaultdict(lambda: {"SOL":[None]*12, "NEAR":[None]*12, "sumSOL":0, "sumNEAR":0})
for r in mi:
    y = r["month"][:4]
    i = int(r["month"][5:7]) - 1
    sym = r["symbol"]
    v = num(r["return_pct"])
    if sym in ("SOL","NEAR"):
        cy[y][sym][i] = v
        cy[y]["sum"+sym] += v

contrib_rows = ""
for y in sorted(cy):
    for idx, sym in enumerate(["SOL","NEAR"]):
        arr = cy[y][sym]
        sm = cy[y]["sum"+sym]
        row = f"<tr><td><b>{y if idx == 0 else ''}</b></td><td><b>{sym}</b></td>"
        for v in arr:
            row += "<td>—</td>" if v is None else f'<td class="{cls(v)}">{plus(v)}{fmt(v,1)}%</td>'
        row += f'<td class="{cls(sm)}"><b>{plus(sm)}{fmt(sm,1)}%</b></td></tr>'
        contrib_rows += row

inst_rows = ""
for x in inst:
    inst_rows += f'''
    <tr>
      <td><b>{x.get("symbol","")}</b></td>
      <td class="{cls(x.get("return_pct"))}">{plus(x.get("return_pct"))}{fmt(x.get("return_pct"))}%</td>
      <td><b>{fmt(x.get("share_of_return_pct"))}%</b></td>
      <td><b>{fmt(x.get("trades"),0)}</b></td>
      <td><span class="green">{fmt(x.get("wins"),0)}</span> / <span class="red">{fmt(x.get("losses"),0)}</span></td>
    </tr>'''

labels_eq = [r["month"] for r in equity]
data_eq = [num(r.get("equity") or r.get("end_eq")) for r in equity]
labels_dd = [r["month"] for r in dd]
data_dd = [-abs(num(r.get("drawdown_pct"))) for r in dd]

sol = next((x for x in inst if x.get("symbol") == "SOL"), {})
near = next((x for x in inst if x.get("symbol") == "NEAR"), {})
trade_pie = [num(sol.get("trades")), num(near.get("trades"))]
wl_pie = [num(sol.get("wins")) + num(near.get("wins")), num(sol.get("losses")) + num(near.get("losses"))]

html = f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>TrendFrend Risk 1.0</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{{--line:rgba(255,255,255,.10);--text:#f5f5f7;--muted:#9ca3af;--green:#30d158;--red:#ff453a;--blue:#0a84ff}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(circle at 18% 0,rgba(10,132,255,.22),transparent 34%),radial-gradient(circle at 85% 0,rgba(48,209,88,.13),transparent 30%),linear-gradient(180deg,#05070a,#070a0f);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.app{{display:grid;grid-template-columns:275px 1fr;min-height:100vh}}
aside{{position:sticky;top:0;height:100vh;padding:26px 18px;border-right:1px solid var(--line);background:rgba(7,12,18,.88)}}
.logo{{width:52px;height:52px;border-radius:14px;background:linear-gradient(145deg,#fff,#b8bec8);color:#05070a;display:grid;place-items:center;font-weight:900;font-size:26px}}
.brand{{display:flex;gap:14px;align-items:center;margin-bottom:34px}}.brand h1{{margin:0;font-size:25px}}.brand p{{margin:5px 0 0;color:var(--muted);font-size:13px}}
nav a{{display:block;color:#d1d5db;text-decoration:none;padding:13px 16px;border-radius:15px;margin:6px 0;font-size:15px}}nav a.active{{background:rgba(255,255,255,.09);color:#fff;border-left:4px solid var(--green)}}
.side-card{{border:1px solid var(--line);border-radius:18px;padding:18px;background:rgba(255,255,255,.045);margin-top:190px}}.side-card+.side-card{{margin-top:16px}}.side-card h3{{color:var(--green)}}
main{{padding:28px 34px 40px}}.top{{display:flex;justify-content:space-between;align-items:start;margin-bottom:20px}}
.title h2{{font-size:42px;margin:0 0 7px}}.title p{{margin:0;color:#9fb4c9;font-size:16px}}.badge{{font-size:13px;color:var(--green);border:1px solid rgba(48,209,88,.4);border-radius:999px;padding:5px 10px;margin-left:10px}}.pill{{border:1px solid var(--line);border-radius:999px;padding:12px 18px;background:rgba(255,255,255,.06)}}
.grid{{display:grid;gap:14px}}.kpis{{grid-template-columns:repeat(8,1fr);margin-bottom:14px}}.charts{{grid-template-columns:1fr 1fr;margin-bottom:14px}}.lower{{grid-template-columns:1fr 1fr;margin-bottom:14px}}.bottom{{grid-template-columns:1.35fr .65fr}}
.card{{border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,rgba(255,255,255,.07),rgba(255,255,255,.035));padding:16px;box-shadow:0 20px 55px rgba(0,0,0,.35);overflow:hidden}}
.label{{color:#c7c7cc;font-size:13px}}.value{{font-size:25px;font-weight:850;letter-spacing:-.03em;margin:8px 0 5px}}.sub{{color:var(--muted);font-size:13px}}.green{{color:var(--green)}}.red{{color:var(--red)}}
.section{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}}.section h3{{margin:0;font-size:18px}}.section span{{color:var(--muted);font-size:13px}}
.chart-card{{height:330px}}.chart-card canvas{{width:100%!important;height:255px!important}}
.mini-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.mini{{border:1px solid var(--line);border-radius:14px;padding:13px;background:rgba(0,0,0,.15)}}.mini b{{display:block;font-size:22px;margin:6px 0}}
.pie-stack{{display:grid;grid-template-columns:1fr;gap:16px}}.pie-box{{border:1px solid var(--line);border-radius:14px;padding:12px;background:rgba(0,0,0,.15)}}.pie-box canvas{{height:220px!important}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}th{{color:var(--muted)}}
.table-wrap{{overflow:auto}}.table-wrap table{{min-width:1050px}}
@media(max-width:1200px){{.app{{grid-template-columns:1fr}}aside{{display:none}}.kpis,.charts,.lower,.bottom{{grid-template-columns:1fr}}.mini-grid{{grid-template-columns:1fr 1fr}}}}
</style>
</head>
<body>
<div class="app">
<aside>
<div class="brand"><div class="logo">T</div><div><h1>TrendFrend</h1><p>Risk 1.0 Final</p></div></div>
<nav><a class="active">⌘ Обзор</a><a>↗ Производительность</a><a>▦ Помесячно</a><a>◎ Инструменты</a><a>⚙ Настройки</a></nav>
<div class="side-card"><div class="label">Режим</div><h3>Risk 1.0% / month</h3><p>Monthly Fixed-Return<br><b>Compounding</b></p></div>
<div class="side-card"><div class="label">Сравнение</div><h3>Профиль риска</h3><p>Risk per Month: <b>1.00%</b></p><p>MaxDD: <b>{fmt(max_dd)}%</b></p></div>
</aside>
<main>
<div class="top"><div class="title"><h2>TrendFrend <span class="badge">RISK 1.0% FINAL</span></h2><p>Monthly Fixed-Return Compounding • данные только из out_risk_1pct_monthly</p></div><div class="pill">СТАТИЧЕСКАЯ АНАЛИТИКА</div></div>
<div class="grid kpis">{kpis}</div>
<div class="grid charts">
<div class="card chart-card"><div class="section"><h3>Кривая капитала</h3><span>Final Equity: {sci(data_eq[-1])}</span></div><canvas id="eq"></canvas></div>
<div class="card chart-card"><div class="section"><h3>Кривая просадки</h3><span>Шкала 0…-100% · MaxDD {fmt(max_dd)}%</span></div><canvas id="dd"></canvas></div>
</div>
<div class="grid lower">
<div class="card"><div class="section"><h3>Помесячная сводка</h3><span>Risk 1.0%</span></div><div class="mini-grid">{month_summary}</div></div>
<div class="card"><div class="section"><h3>Сравнение риска</h3><span>1.0% vs 0.5%</span></div><div class="mini-grid">{risk_compare}</div></div>
</div>
<div class="grid bottom">
<div class="card">
<div class="section"><h3>Помесячная доходность (%)</h3><span>monthly.csv</span></div>
<table><thead><tr><th>Год</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th><th>Итого</th></tr></thead><tbody>{monthly_rows}</tbody></table>
<div style="margin-top:18px" class="section"><h3>Ежемесячный вклад инструментов</h3><span>monthly_instruments.csv</span></div>
<div class="table-wrap"><table><thead><tr><th>Год</th><th>Инструмент</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th><th>Итого</th></tr></thead><tbody>{contrib_rows}</tbody></table></div>
</div>
<div class="card">
<div class="section"><h3>Инструменты</h3><span>instrument_summary.csv</span></div>
<div class="pie-stack">
<div class="pie-box"><div class="label">Соотношение сделок</div><canvas id="tradePie"></canvas></div>
<div class="pie-box"><div class="label">Прибыльные / убыточные</div><canvas id="wlPie"></canvas></div>
</div>
<table style="margin-top:14px"><thead><tr><th>Инструмент</th><th>Доходность</th><th>Доля</th><th>Сделок</th><th>Win / Loss</th></tr></thead><tbody>{inst_rows}</tbody></table>
</div>
</div>
</main>
</div>
<script>
const labelsEq={json.dumps(labels_eq)};
const dataEq={json.dumps(data_eq)};
const labelsDd={json.dumps(labels_dd)};
const dataDd={json.dumps(data_dd)};
new Chart(document.getElementById('eq'),{{type:'line',data:{{labels:labelsEq,datasets:[{{data:dataEq,borderColor:'#30d158',backgroundColor:'rgba(48,209,88,.22)',borderWidth:2,tension:.22,pointRadius:0,fill:true}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}},ticks:{{color:'#8b8f98',maxTicksLimit:8}}}},y:{{grid:{{color:'rgba(255,255,255,.08)'}},ticks:{{color:'#8b8f98'}}}}}}}}}});
new Chart(document.getElementById('dd'),{{type:'line',data:{{labels:labelsDd,datasets:[{{data:dataDd,borderColor:'#ff453a',backgroundColor:'rgba(255,69,58,.18)',borderWidth:2,tension:.22,pointRadius:0,fill:true}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}},ticks:{{color:'#8b8f98',maxTicksLimit:8}}}},y:{{min:-100,max:0,grid:{{color:'rgba(255,255,255,.08)'}},ticks:{{color:'#8b8f98',stepSize:10,callback:v=>v+'%'}}}}}}}}}});
new Chart(document.getElementById('tradePie'),{{type:'doughnut',data:{{labels:['SOL','NEAR'],datasets:[{{data:{json.dumps(trade_pie)},backgroundColor:['#30d158','#0a84ff'],borderWidth:0}}]}},options:{{plugins:{{legend:{{position:'right',labels:{{color:'#c7c7cc'}}}}}},cutout:'58%'}}}});
new Chart(document.getElementById('wlPie'),{{type:'doughnut',data:{{labels:['Прибыльные','Убыточные'],datasets:[{{data:{json.dumps(wl_pie)},backgroundColor:['#30d158','#ff453a'],borderWidth:0}}]}},options:{{plugins:{{legend:{{position:'right',labels:{{color:'#c7c7cc'}}}}}},cutout:'58%'}}}});
</script>
</body>
</html>'''

(OUT / "risk1-final.html").write_text(html, encoding="utf-8")
print("built:", OUT / "risk1-final.html")
