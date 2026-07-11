import csv, json, math
from pathlib import Path

ROOT = Path("/home/ubuntu/.hermes/bots/champion_live_bot/public_report")
SRC = Path("/tmp/grid_3m_1h/out_risk_05pct_monthly")
OUT = ROOT / "trendfrend-risk05"
OUT.mkdir(parents=True, exist_ok=True)

REQ = [
    "summary.json",
    "summary.csv",
    "monthly.csv",
    "yearly.csv",
    "trades.csv",
    "equity_curve_monthly.csv",
    "drawdown_monthly.csv",
    "instrument_summary.csv",
    "monthly_instruments.csv",
]
for f in REQ:
    if not (SRC / f).exists():
        raise SystemExit(f"ERROR: missing {SRC / f}")

def read_csv(name):
    with (SRC / name).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def num(x):
    if x is None:
        return 0.0
    return float(str(x).replace("%", "").replace(",", "").strip() or 0)

summary = json.loads((SRC / "summary.json").read_text(encoding="utf-8"))
monthly = read_csv("monthly.csv")
yearly = read_csv("yearly.csv")
equity = read_csv("equity_curve_monthly.csv")
dd = read_csv("drawdown_monthly.csv")
inst = read_csv("instrument_summary.csv")
mi = read_csv("monthly_instruments.csv")

payload = {
    "summary": summary,
    "monthly": monthly,
    "yearly": yearly,
    "equity": equity,
    "drawdown": dd,
    "instruments": inst,
    "monthly_instruments": mi,
}

payload_json = json.dumps(payload, ensure_ascii=False)

html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>TrendFrend Risk 0.5</title>
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
.label{{color:#c7c7cc;font-size:13px}}.value{{font-size:27px;font-weight:850;letter-spacing:-.03em;margin:8px 0 5px}}.sub{{color:var(--muted);font-size:13px}}.green{{color:var(--green)}}.red{{color:var(--red)}}
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
<div class="brand"><div class="logo">T</div><div><h1>TrendFrend</h1><p>Risk 0.5 Dashboard</p></div></div>
<nav><a class="active">⌘ Обзор</a><a>↗ Производительность</a><a>▦ Помесячно</a><a>◎ Инструменты</a><a>⚙ Настройки</a></nav>
<div class="side-card"><div class="label">Risk Profile</div><h3>0.5% / month</h3><p>MaxDD<br><b>13.79%</b></p><p>PF<br><b>2.04</b></p></div>
<div class="side-card"><div class="label">Сравнение с 1%</div><h3>DD снижена ×2</h3><p>26.04% → 13.79%</p><p>Сделок: <b>15,033</b></p></div>
</aside>

<main>
<div class="top"><div class="title"><h2>TrendFrend <span class="badge">RISK 0.5%</span></h2><p>Monthly Fixed-Return Compounding • Risk per Month 0.5%</p></div><div class="pill">СТАТИЧЕСКАЯ АНАЛИТИКА</div></div>

<div class="grid kpis" id="kpis"></div>

<div class="grid charts">
<div class="card chart-card"><div class="section"><h3>Кривая капитала</h3><span id="eqNote"></span></div><canvas id="eq"></canvas></div>
<div class="card chart-card"><div class="section"><h3>Кривая просадки</h3><span id="ddNote"></span></div><canvas id="dd"></canvas></div>
</div>

<div class="grid lower">
<div class="card"><div class="section"><h3>Помесячная сводка</h3><span>лучший / худший / средний</span></div><div class="mini-grid" id="monthSummary"></div></div>
<div class="card"><div class="section"><h3>Сравнение риска</h3><span>1.0% vs 0.5%</span></div><div class="mini-grid" id="riskCompare"></div></div>
</div>

<div class="grid bottom">
<div class="card">
<div class="section"><h3>Помесячная доходность (%)</h3><span>66 месяцев</span></div>
<table><thead><tr><th>Год</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th><th>Итого</th></tr></thead><tbody id="monthlyTable"></tbody></table>

<div style="margin-top:18px" class="section"><h3>Ежемесячный вклад инструментов</h3><span>SOL / NEAR</span></div>
<div class="table-wrap"><table><thead><tr><th>Год</th><th>Инструмент</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th><th>Итого</th></tr></thead><tbody id="contribTable"></tbody></table></div>
</div>

<div class="card">
<div class="section"><h3>Инструменты</h3><span>структура сделок / результат</span></div>
<div class="pie-stack">
<div class="pie-box"><div class="label">Соотношение сделок</div><canvas id="tradePie"></canvas></div>
<div class="pie-box"><div class="label">Прибыльные / убыточные</div><canvas id="wlPie"></canvas></div>
</div>
<table style="margin-top:14px"><thead><tr><th>Инструмент</th><th>Вклад</th><th>Доля</th><th>Сделок</th><th>Win / Loss</th></tr></thead><tbody id="instTable"></tbody></table>
</div>
</div>
</main>
</div>

<script>
const DATA = {payload_json};
const s=DATA.summary,m=DATA.monthly,eq=DATA.equity,dd=DATA.drawdown,isum=DATA.instruments,mi=DATA.monthly_instruments;
const fmt=(v,d=2)=>Number(String(v||0).replace('%','')).toLocaleString('en-US',{{minimumFractionDigits:d,maximumFractionDigits:d}});
const num=v=>Number(String(v||0).replace('%','').replace(/,/g,''));
const plus=v=>num(v)>=0?'+':''; const cls=v=>num(v)>=0?'green':'red';
function kpi(l,v,sub,c=''){{return `<div class="card"><div class="label">${{l}}</div><div class="value ${{c}}">${{v}}</div><div class="sub">${{sub}}</div></div>`}}
function mini(l,v,sub,c=''){{return `<div class="mini"><span class="label">${{l}}</span><b class="${{c}}">${{v}}</b><span class="sub">${{sub}}</span></div>`}}
function line(id,labels,data,color,fill,ddScale=false){{
 new Chart(document.getElementById(id),{{type:'line',data:{{labels,datasets:[{{data,borderColor:color,backgroundColor:fill,borderWidth:2,tension:.22,pointRadius:0,fill:true}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}},ticks:{{color:'#8b8f98',maxTicksLimit:8}}}},y:ddScale?{{min:-100,max:0,grid:{{color:'rgba(255,255,255,.08)'}},ticks:{{color:'#8b8f98',stepSize:10,callback:v=>fmt(v,0)+'%'}}}}:{{grid:{{color:'rgba(255,255,255,.08)'}},ticks:{{color:'#8b8f98',callback:v=>fmt(v,0)+'%'}}}}}}}}}});
}}

const totalRet = num(s.total_return_pct ?? s.return_pct ?? s.total_return);
const maxDD = num(s.max_dd_pct ?? s.max_drawdown_pct);
const pf = num(s.profit_factor);
const wr = num(s.win_rate_pct ?? s.win_rate);
const trades = num(s.total_trades);
const avgTrade = num(s.avg_trade_return_pct);
const avgHold = num(s.avg_hold_hours);
const avgMonthly = num(s.avg_monthly_return_pct ?? s.avg_monthly_return);
const avgTradesMonth = trades / m.length;
const recovery = totalRet / maxDD;

kpis.innerHTML=[
kpi('Доходность',`${{plus(totalRet)}}${{fmt(totalRet)}}%`,'за весь период','green'),
kpi('Макс. просадка',`${{fmt(maxDD)}}%`,'month-to-month','red'),
kpi('Средняя доходность сделки',`${{plus(avgTrade)}}${{fmt(avgTrade,3)}}%`,'среднее значение','green'),
kpi('Среднее время сделки',`${{fmt(avgHold,2)}} ч`,'за все сделки'),
kpi('Recovery Factor',fmt(recovery,2),'Recovery','green'),
kpi('Win Rate',`${{fmt(wr)}}%`,'за весь период'),
kpi('Всего сделок',fmt(trades,0),`${{m.length}} месяцев`),
kpi('Сделок в месяц',fmt(avgTradesMonth,1),'средняя активность')
].join('');

eqNote.textContent=`Final Equity: $${{fmt(num(eq.at(-1).equity ?? eq.at(-1).end_eq),0)}}`;
ddNote.textContent=`Шкала 0…-100% · max DD ${{fmt(maxDD)}}%`;
line('eq',eq.map(x=>x.month),eq.map(x=>num(x.equity ?? x.end_eq)),'#30d158','rgba(48,209,88,.22)',false);
line('dd',dd.map(x=>x.month),dd.map(x=>-Math.abs(num(x.drawdown_pct))),'#ff453a','rgba(255,69,58,.18)',true);

const best=m.reduce((a,b)=>num(a.return_pct)>num(b.return_pct)?a:b), worst=m.reduce((a,b)=>num(a.return_pct)<num(b.return_pct)?a:b);
const pos=m.filter(x=>num(x.return_pct)>0).length, neg=m.filter(x=>num(x.return_pct)<0).length;
monthSummary.innerHTML=[
mini('Средний месяц',`${{plus(avgMonthly)}}${{fmt(avgMonthly)}}%`,'средняя доходность','green'),
mini('Лучший месяц',`${{plus(num(best.return_pct))}}${{fmt(best.return_pct)}}%`,best.month,'green'),
mini('Худший месяц',`${{plus(num(worst.return_pct))}}${{fmt(worst.return_pct)}}%`,worst.month,'red'),
mini('Прибыльных месяцев',`${{pos}} / ${{m.length}}`,`${{fmt(pos/m.length*100,1)}}%`,'green'),
mini('Убыточных месяцев',`${{neg}} / ${{m.length}}`,`${{fmt(neg/m.length*100,1)}}%`,'red')
].join('');

riskCompare.innerHTML=[
mini('MaxDD 1.0%', '26.04%', 'предыдущий риск','red'),
mini('MaxDD 0.5%', `${{fmt(maxDD)}}%`, 'текущий риск','green'),
mini('Снижение DD', '≈2×', 'просадка ниже','green'),
mini('PF', fmt(pf,4), 'почти без изменений','green'),
mini('Negative months', String(neg), 'месяцев')
].join('');

let by={{}};m.forEach(r=>{{let y=r.month.slice(0,4),i=+r.month.slice(5,7)-1;(by[y]??={{vals:Array(12).fill(null),sum:0}});by[y].vals[i]=num(r.return_pct);by[y].sum+=num(r.return_pct);}});
monthlyTable.innerHTML=Object.keys(by).sort().map(y=>`<tr><td><b>${{y}}</b></td>${{by[y].vals.map(v=>v===null?'<td>—</td>':`<td class="${{cls(v)}}">${{plus(v)}}${{fmt(v,1)}}%</td>`).join('')}}<td class="${{cls(by[y].sum)}}"><b>${{plus(by[y].sum)}}${{fmt(by[y].sum,1)}}%</b></td></tr>`).join('');

let cy={{}};mi.forEach(r=>{{let y=r.month.slice(0,4),i=+r.month.slice(5,7)-1,sym=r.symbol;(cy[y]??={{SOL:Array(12).fill(null),NEAR:Array(12).fill(null),sumSOL:0,sumNEAR:0}});let v=num(r.return_pct);cy[y][sym][i]=v;cy[y]['sum'+sym]+=v;}});
contribTable.innerHTML=Object.keys(cy).sort().map(y=>{{
 let r=cy[y];
 const row=(sym,arr,sum,show)=>`<tr><td><b>${{show?y:''}}</b></td><td><b>${{sym}}</b></td>${{arr.map(v=>v===null?'<td>—</td>':`<td class="${{cls(v)}}">${{plus(v)}}${{fmt(v,1)}}%</td>`).join('')}}<td class="${{cls(sum)}}"><b>${{plus(sum)}}${{fmt(sum,1)}}%</b></td></tr>`;
 return row('SOL',r.SOL,r.sumSOL,true)+row('NEAR',r.NEAR,r.sumNEAR,false);
}}).join('');

const sol=isum.find(x=>x.symbol==='SOL')||{{}}, near=isum.find(x=>x.symbol==='NEAR')||{{}};
new Chart(tradePie,{{type:'doughnut',data:{{labels:['SOL','NEAR'],datasets:[{{data:[num(sol.trades),num(near.trades)],backgroundColor:['#30d158','#0a84ff'],borderWidth:0}}]}},options:{{plugins:{{legend:{{position:'right',labels:{{color:'#c7c7cc'}}}}}},cutout:'58%'}}}});
new Chart(wlPie,{{type:'doughnut',data:{{labels:['Прибыльные','Убыточные'],datasets:[{{data:[num(sol.wins)+num(near.wins),num(sol.losses)+num(near.losses)],backgroundColor:['#30d158','#ff453a'],borderWidth:0}}]}},options:{{plugins:{{legend:{{position:'right',labels:{{color:'#c7c7cc'}}}}}},cutout:'58%'}}}});
instTable.innerHTML=isum.map(x=>`<tr><td><b>${{x.symbol}}</b></td><td class="${{cls(x.return_pct)}}">${{plus(num(x.return_pct))}}${{fmt(x.return_pct)}}%</td><td><b>${{fmt(x.share_of_return_pct)}}%</b></td><td><b>${{fmt(x.trades,0)}}</b></td><td><span class="green">${{fmt(x.wins,0)}}</span> / <span class="red">${{fmt(x.losses,0)}}</span></td></tr>`).join('');
</script>
</body>
</html>"""

(OUT / "index.html").write_text(html, encoding="utf-8")
print("built:", OUT / "index.html")
