import json
from pathlib import Path

ROOT = Path("/home/ubuntu/.hermes/bots/champion_live_bot/public_report")
DATA = ROOT / "data/baseline_v2026_07"
OUT = ROOT / "trendfrend"
OUT.mkdir(exist_ok=True)

summary = json.loads((DATA / "summary.json").read_text())
monthly = json.loads((DATA / "monthly.json").read_text())
drawdown = json.loads((DATA / "drawdown.json").read_text())
isum = json.loads((DATA / "instrument_summary.json").read_text())
icontrib = json.loads((DATA / "instrument_monthly_contribution.json").read_text())

payload = json.dumps({
    "summary": summary,
    "monthly": monthly,
    "drawdown": drawdown,
    "instruments": isum,
    "contrib": icontrib,
}, ensure_ascii=False)

html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>TrendFrend</title>
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
<div class="brand"><div class="logo">T</div><div><h1>TrendFrend</h1><p>торговый алгоритм</p></div></div>
<nav><a class="active">⌘ Обзор</a><a>↗ Производительность</a><a>▦ Помесячно</a><a>◎ Инструменты</a><a>⚙ Настройки</a></nav>
<div class="side-card"><div class="label">Параметры стратегии</div><h3>SOL 70%<br>NEAR 30%</h3><p>Таймфрейм входа <b style="float:right">3m</b></p><p>Таймфрейм тренда <b style="float:right">1h</b></p></div>
<div class="side-card"><div class="label">Режим оценки</div><h3>Фиксированный капитал</h3><p>Начальный капитал<br><b>1,000 USDT</b></p><p>Период<br><b>2021-01 — 2026-06</b></p></div>
</aside>

<main>
<div class="top"><div class="title"><h2>TrendFrend <span class="badge">BASELINE v2026-07</span></h2><p>SOL 70% / NEAR 30% • 3m / 1h • фиксированный начальный капитал</p></div><div class="pill">СТАТИЧЕСКАЯ АНАЛИТИКА</div></div>
<div class="grid kpis" id="kpis"></div>

<div class="grid charts">
<div class="card chart-card"><div class="section"><h3>Кривая капитала</h3><span id="eqNote"></span></div><canvas id="eq"></canvas></div>
<div class="card chart-card"><div class="section"><h3>Кривая просадки</h3><span id="ddNote"></span></div><canvas id="dd"></canvas></div>
</div>

<div class="grid lower">
<div class="card"><div class="section"><h3>Помесячная сводка</h3><span>лучший / худший / средний</span></div><div class="mini-grid" id="monthSummary"></div></div>
<div class="card"><div class="section"><h3>Ключевые показатели стратегии</h3><span>риск / качество / серии</span></div><div class="mini-grid" id="strategyStats"></div></div>
</div>

<div class="grid bottom">
<div class="card">
<div class="section"><h3>Помесячная доходность (%)</h3><span>все месяцы</span></div>
<table><thead><tr><th>Год</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th><th>Итого</th></tr></thead><tbody id="monthlyTable"></tbody></table>

<div style="margin-top:18px" class="section"><h3>Ежемесячный вклад инструментов в доходность (%)</h3><span>SOL / NEAR по месяцам</span></div>
<div class="table-wrap"><table><thead><tr><th>Год</th><th>Инструмент</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th><th>Итого</th></tr></thead><tbody id="contribTable"></tbody></table></div>
</div>

<div class="card">
<div class="section"><h3>Инструменты</h3><span>структура сделок / результат</span></div>
<div class="pie-stack">
<div class="pie-box"><div class="label">Соотношение сделок</div><canvas id="tradePie"></canvas></div>
<div class="pie-box"><div class="label">Прибыльные / убыточные сделки</div><canvas id="wlPie"></canvas></div>
</div>
<table style="margin-top:14px"><thead><tr><th>Инструмент</th><th>Вклад</th><th>Доля</th><th>Сделок</th><th>Win / Loss</th></tr></thead><tbody id="instTable"></tbody></table>
</div>
</div>
</main>
</div>

<script>
const DATA = {payload};
const s=DATA.summary,m=DATA.monthly,d=DATA.drawdown,isum=DATA.instruments,icontrib=DATA.contrib;
const fmt=(v,d=2)=>Number(v||0).toLocaleString('en-US',{{minimumFractionDigits:d,maximumFractionDigits:d}});
const plus=v=>Number(v)>=0?'+':''; const cls=v=>Number(v)>=0?'green':'red';
function kpi(l,v,sub,c=''){{return `<div class="card"><div class="label">${{l}}</div><div class="value ${{c}}">${{v}}</div><div class="sub">${{sub}}</div></div>`}}
function mini(l,v,sub,c=''){{return `<div class="mini"><span class="label">${{l}}</span><b class="${{c}}">${{v}}</b><span class="sub">${{sub}}</span></div>`}}
function hours(h){{if(!h)return '—';let hh=Math.floor(h),mm=Math.round((h-hh)*60);return `${{hh}}ч ${{mm}}м`;}}
function line(id,labels,data,color,fill){{new Chart(document.getElementById(id),{{type:'line',data:{{labels,datasets:[{{data,borderColor:color,backgroundColor:fill,borderWidth:2,tension:.24,pointRadius:0,fill:true}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}},ticks:{{color:'#8b8f98',maxTicksLimit:8}}}},y:{{grid:{{color:'rgba(255,255,255,.08)'}},ticks:{{color:'#8b8f98',callback:v=>fmt(v,0)+'%'}}}}}}}}}})}}

const cum=[];let c=0;m.forEach(x=>{{c+=Number(x.return_pct||0);cum.push({{month:x.month,v:+c.toFixed(2)}})}});

kpis.innerHTML=[
kpi('Доходность',`${{plus(s.total_return_pct_summary)}}${{fmt(s.total_return_pct_summary)}}%`,'за весь период',cls(s.total_return_pct_summary)),
kpi('Макс. просадка',`${{fmt(s.max_drawdown_pct)}}%`,'за весь период','red'),
kpi('Средняя доходность сделки',`${{plus(s.avg_trade_return_pct)}}${{fmt(s.avg_trade_return_pct,3)}}%`,'среднее значение',cls(s.avg_trade_return_pct)),
kpi('Среднее время сделки',hours(s.avg_hold_hours),'за все сделки'),
kpi('Recovery Factor',fmt(s.recovery_factor,2),'Recovery','green'),
kpi('Win Rate',`${{fmt(s.win_rate)}}%`,'за весь период'),
kpi('Всего сделок',fmt(s.total_trades,0),`${{s.total_months}} месяцев`),
kpi('Сделок в месяц',fmt(s.avg_trades_per_month,1),'средняя активность')
].join('');

eqNote.textContent=`Итог ${{plus(s.total_return_pct_summary)}}${{fmt(s.total_return_pct_summary)}}%`;
ddNote.textContent=`Макс. просадка ${{fmt(s.max_drawdown_pct)}}%`;
line('eq',cum.map(x=>x.month),cum.map(x=>x.v),'#30d158','rgba(48,209,88,.22)');
line('dd',d.map(x=>x.month),d.map(x=>-Math.abs(x.drawdown_pct)),'#ff453a','rgba(255,69,58,.18)');

const best=m.reduce((a,b)=>a.return_pct>b.return_pct?a:b), worst=m.reduce((a,b)=>a.return_pct<b.return_pct?a:b);
monthSummary.innerHTML=[
mini('Средний месяц',`${{plus(s.avg_monthly_return)}}${{fmt(s.avg_monthly_return)}}%`,'средняя доходность','green'),
mini('Лучший месяц',`${{plus(best.return_pct)}}${{fmt(best.return_pct)}}%`,best.month,'green'),
mini('Худший месяц',`${{plus(worst.return_pct)}}${{fmt(worst.return_pct)}}%`,worst.month,'red'),
mini('Прибыльных месяцев',`${{s.positive_months}} / ${{s.total_months}}`,`${{fmt(s.positive_months/s.total_months*100,1)}}%`,'green'),
mini('Убыточных месяцев',`${{s.negative_months}} / ${{s.total_months}}`,`${{fmt(s.negative_months/s.total_months*100,1)}}%`,'red')
].join('');

strategyStats.innerHTML=[
mini('Средний риск на сделку',s.avg_risk_per_trade_pct?`${{fmt(s.avg_risk_per_trade_pct,3)}}%`:'—','от капитала'),
mini('Среднее R/R',s.avg_risk_reward?fmt(s.avg_risk_reward,2):'—','R:R','green'),
mini('Профит-фактор',fmt(s.profit_factor,4),'PF','green'),
mini('Макс. серия убытков',fmt(s.max_loss_streak,0),'сделок','red'),
mini('Макс. серия прибыли',fmt(s.max_win_streak,0),'сделок','green')
].join('');

let by={{}};m.forEach(r=>{{let y=r.month.slice(0,4),i=+r.month.slice(5,7)-1;(by[y]??={{vals:Array(12).fill(null),sum:0}});by[y].vals[i]=r.return_pct;by[y].sum+=r.return_pct;}});
monthlyTable.innerHTML=Object.keys(by).sort().map(y=>`<tr><td><b>${{y}}</b></td>${{by[y].vals.map(v=>v===null?'<td>—</td>':`<td class="${{cls(v)}}">${{plus(v)}}${{fmt(v,1)}}%</td>`).join('')}}<td class="${{cls(by[y].sum)}}"><b>${{plus(by[y].sum)}}${{fmt(by[y].sum,1)}}%</b></td></tr>`).join('');

let cy={{}};icontrib.forEach(r=>{{let y=r.month.slice(0,4),i=+r.month.slice(5,7)-1;cy[y]??={{SOL:Array(12).fill(null),NEAR:Array(12).fill(null),total:Array(12).fill(null),sumSOL:0,sumNEAR:0,sumTotal:0}};let sv=Number(r.symbols.SOL.contribution_pct||0),nv=Number(r.symbols.NEAR.contribution_pct||0),tv=Number(r.total_return_pct||0);cy[y].SOL[i]=sv;cy[y].NEAR[i]=nv;cy[y].total[i]=tv;cy[y].sumSOL+=sv;cy[y].sumNEAR+=nv;cy[y].sumTotal+=tv;}});
contribTable.innerHTML=Object.keys(cy).sort().map(y=>{{
 let r=cy[y];
 const row=(name,arr,sum,showYear)=>`<tr><td><b>${{showYear?y:''}}</b></td><td><b>${{name}}</b></td>${{arr.map(v=>v===null?'<td>—</td>':`<td class="${{cls(v)}}">${{plus(v)}}${{fmt(v,1)}}%</td>`).join('')}}<td class="${{cls(sum)}}"><b>${{plus(sum)}}${{fmt(sum,1)}}%</b></td></tr>`;
 return row('SOL',r.SOL,r.sumSOL,true)+row('NEAR',r.NEAR,r.sumNEAR,false)+row('Итого',r.total,r.sumTotal,false);
}}).join('');

const sol=isum.find(x=>x.symbol==='SOL')||{{}}, near=isum.find(x=>x.symbol==='NEAR')||{{}};
new Chart(tradePie,{{type:'doughnut',data:{{labels:['SOL','NEAR'],datasets:[{{data:[sol.trades||0,near.trades||0],backgroundColor:['#30d158','#0a84ff'],borderWidth:0}}]}},options:{{plugins:{{legend:{{position:'right',labels:{{color:'#c7c7cc'}}}}}},cutout:'58%'}}}});
new Chart(wlPie,{{type:'doughnut',data:{{labels:['Прибыльные','Убыточные'],datasets:[{{data:[(sol.wins||0)+(near.wins||0),(sol.losses||0)+(near.losses||0)],backgroundColor:['#30d158','#ff453a'],borderWidth:0}}]}},options:{{plugins:{{legend:{{position:'right',labels:{{color:'#c7c7cc'}}}}}},cutout:'58%'}}}});
instTable.innerHTML=isum.map(x=>`<tr><td><b>${{x.symbol}}</b></td><td class="${{cls(x.contribution_pct)}}">${{plus(x.contribution_pct)}}${{fmt(x.contribution_pct)}}%</td><td><b>${{fmt(x.share_of_return_pct)}}%</b></td><td><b>${{fmt(x.trades,0)}}</b></td><td><span class="green">${{fmt(x.wins,0)}}</span> / <span class="red">${{fmt(x.losses,0)}}</span></td></tr>`).join('');
</script>
</body>
</html>"""

(OUT / "index.html").write_text(html)
print("rebuilt", OUT / "index.html")
