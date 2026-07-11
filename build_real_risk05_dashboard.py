import csv, json, math
from pathlib import Path

SRC = Path(__import__("os").environ["SRC"])
OUT = Path("/home/ubuntu/.hermes/bots/champion_live_bot/public_report/trendfrend")
OUT.mkdir(parents=True, exist_ok=True)

def read_csv(name):
    with (SRC / name).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def js_payload(obj):
    return json.dumps(obj, ensure_ascii=False)

summary = json.loads((SRC / "summary.json").read_text(encoding="utf-8"))
payload = {
    "summary": summary,
    "monthly": read_csv("monthly.csv"),
    "equity": read_csv("equity_curve_monthly.csv"),
    "drawdown": read_csv("drawdown_monthly.csv"),
    "instruments": read_csv("instrument_summary.csv"),
    "monthly_instruments": read_csv("monthly_instruments.csv"),
}

template = Path("trendfrend/index.html").read_text(encoding="utf-8")

start = template.find("const DATA = ")
if start == -1:
    raise SystemExit("ERROR: в trendfrend/index.html не найден const DATA")

script_start = template.rfind("<script>", 0, start)
script_end = template.find("</script>", start) + len("</script>")

new_script = f"""
<script>
const DATA = {js_payload(payload)};
const s=DATA.summary,m=DATA.monthly,eq=DATA.equity,dd=DATA.drawdown,isum=DATA.instruments,mi=DATA.monthly_instruments;
const num=v=>Number(String(v??0).replace('%','').replace(/,/g,''));
const fmt=(v,d=2)=>num(v).toLocaleString('en-US',{{minimumFractionDigits:d,maximumFractionDigits:d}});
const plus=v=>num(v)>=0?'+':''; const cls=v=>num(v)>=0?'green':'red';
function kpi(l,v,sub,c=''){{return `<div class="card"><div class="label">${{l}}</div><div class="value ${{c}}">${{v}}</div><div class="sub">${{sub}}</div></div>`}}
function mini(l,v,sub,c=''){{return `<div class="mini"><span class="label">${{l}}</span><b class="${{c}}">${{v}}</b><span class="sub">${{sub}}</span></div>`}}
function sci(v){{return Number(v).toExponential(2).replace('e+',' × 10^');}}

function line(id,labels,data,color,fill,ddScale=false){{
 new Chart(document.getElementById(id),{{type:'line',data:{{labels,datasets:[{{data,borderColor:color,backgroundColor:fill,borderWidth:2,tension:.22,pointRadius:0,fill:true}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}},ticks:{{color:'#8b8f98',maxTicksLimit:8}}}},y:ddScale?{{min:-100,max:0,grid:{{color:'rgba(255,255,255,.08)'}},ticks:{{color:'#8b8f98',stepSize:10,callback:v=>fmt(v,0)+'%'}}}}:{{grid:{{color:'rgba(255,255,255,.08)'}},ticks:{{color:'#8b8f98',callback:v=>fmt(v,0)+'%'}}}}}}}}}});
}}

const totalRet=num(s.total_return_pct);
const maxDD=num(s.max_dd_pct ?? s.max_drawdown_pct);
const pf=num(s.profit_factor);
const wr=num(s.win_rate_pct ?? s.win_rate);
const trades=num(s.total_trades);
const avgTrade=num(s.avg_trade_return_pct);
const avgHold=num(s.avg_hold_hours);
const avgMonthly=num(s.avg_monthly_return_pct);
const pos=num(s.positive_months);
const neg=num(s.negative_months);
const avgTradesMonth=trades/m.length;

document.title='TrendFrend Risk 0.5';
document.querySelector('.brand p').textContent='Risk 0.5 Dashboard';
document.querySelector('.title h2').innerHTML='TrendFrend <span class="badge">RISK 0.5%</span>';
document.querySelector('.title p').textContent='Monthly Fixed-Return Compounding • Risk per Month 0.5%';

kpis.innerHTML=[
kpi('Доходность',sci(totalRet)+'%','Monthly Fixed-Return Compounding','green'),
kpi('Макс. просадка',fmt(maxDD)+'%','month-to-month','red'),
kpi('Средняя доходность сделки',plus(avgTrade)+fmt(avgTrade,3)+'%','среднее значение','green'),
kpi('Среднее время сделки',fmt(avgHold,2)+' ч','за все сделки'),
kpi('Profit Factor',fmt(pf,4),'PF','green'),
kpi('Win Rate',fmt(wr)+'%','за весь период'),
kpi('Всего сделок',fmt(trades,0),m.length+' месяцев'),
kpi('Сделок в месяц',fmt(avgTradesMonth,1),'средняя активность')
].join('');

eqNote.textContent='Final Equity: '+sci(eq.at(-1).equity ?? eq.at(-1).end_eq);
ddNote.textContent='Шкала 0…-100% · max DD '+fmt(maxDD)+'%';

line('eq',eq.map(x=>x.month),eq.map(x=>num(x.equity ?? x.end_eq)),'#30d158','rgba(48,209,88,.22)',false);
line('dd',dd.map(x=>x.month),dd.map(x=>-Math.abs(num(x.drawdown_pct))),'#ff453a','rgba(255,69,58,.18)',true);

const best=m.reduce((a,b)=>num(a.return_pct)>num(b.return_pct)?a:b);
const worst=m.reduce((a,b)=>num(a.return_pct)<num(b.return_pct)?a:b);

monthSummary.innerHTML=[
mini('Средний месяц',plus(avgMonthly)+fmt(avgMonthly)+'%','средняя доходность','green'),
mini('Лучший месяц',plus(best.return_pct)+fmt(best.return_pct)+'%',best.month,'green'),
mini('Худший месяц',plus(worst.return_pct)+fmt(worst.return_pct)+'%',worst.month,'red'),
mini('Прибыльных месяцев',pos+' / '+m.length,fmt(pos/m.length*100,1)+'%','green'),
mini('Убыточных месяцев',neg+' / '+m.length,fmt(neg/m.length*100,1)+'%','red')
].join('');

strategyStats.innerHTML=[
mini('Risk per Month','0.50%','Monthly Fixed-Return Compounding','green'),
mini('Профит-фактор',fmt(pf,4),'PF','green'),
mini('MaxDD 1.0%','26.04%','предыдущий риск','red'),
mini('MaxDD 0.5%',fmt(maxDD)+'%','текущий риск','green'),
mini('Снижение DD','≈2×','просадка ниже','green')
].join('');

let by={{}};
m.forEach(r=>{{let y=r.month.slice(0,4),i=+r.month.slice(5,7)-1;(by[y]??={{vals:Array(12).fill(null),sum:0}});by[y].vals[i]=num(r.return_pct);by[y].sum+=num(r.return_pct);}});
monthlyTable.innerHTML=Object.keys(by).sort().map(y=>`<tr><td><b>${{y}}</b></td>${{by[y].vals.map(v=>v===null?'<td>—</td>':`<td class="${{cls(v)}}">${{plus(v)}}${{fmt(v,1)}}%</td>`).join('')}}<td class="${{cls(by[y].sum)}}"><b>${{plus(by[y].sum)}}${{fmt(by[y].sum,1)}}%</b></td></tr>`).join('');

let cy={{}};
mi.forEach(r=>{{let y=r.month.slice(0,4),i=+r.month.slice(5,7)-1,sym=r.symbol;(cy[y]??={{SOL:Array(12).fill(null),NEAR:Array(12).fill(null),sumSOL:0,sumNEAR:0}});let v=num(r.return_pct);cy[y][sym][i]=v;cy[y]['sum'+sym]+=v;}});
contribTable.innerHTML=Object.keys(cy).sort().map(y=>{{let r=cy[y];const row=(sym,arr,sum,show)=>`<tr><td><b>${{show?y:''}}</b></td><td><b>${{sym}}</b></td>${{arr.map(v=>v===null?'<td>—</td>':`<td class="${{cls(v)}}">${{plus(v)}}${{fmt(v,1)}}%</td>`).join('')}}<td class="${{cls(sum)}}"><b>${{plus(sum)}}${{fmt(sum,1)}}%</b></td></tr>`;return row('SOL',r.SOL,r.sumSOL,true)+row('NEAR',r.NEAR,r.sumNEAR,false);}}).join('');

const sol=isum.find(x=>x.symbol==='SOL')||{{}}, near=isum.find(x=>x.symbol==='NEAR')||{{}};
new Chart(tradePie,{{type:'doughnut',data:{{labels:['SOL','NEAR'],datasets:[{{data:[num(sol.trades),num(near.trades)],backgroundColor:['#30d158','#0a84ff'],borderWidth:0}}]}},options:{{plugins:{{legend:{{position:'right',labels:{{color:'#c7c7cc'}}}}}},cutout:'58%'}}}});
new Chart(wlPie,{{type:'doughnut',data:{{labels:['Прибыльные','Убыточные'],datasets:[{{data:[num(sol.wins)+num(near.wins),num(sol.losses)+num(near.losses)],backgroundColor:['#30d158','#ff453a'],borderWidth:0}}]}},options:{{plugins:{{legend:{{position:'right',labels:{{color:'#c7c7cc'}}}}}},cutout:'58%'}}}});
instTable.innerHTML=isum.map(x=>`<tr><td><b>${{x.symbol}}</b></td><td class="${{cls(x.return_pct)}}">${{plus(x.return_pct)}}${{fmt(x.return_pct)}}%</td><td><b>${{fmt(x.share_of_return_pct)}}%</b></td><td><b>${{fmt(x.trades,0)}}</b></td><td><span class="green">${{fmt(x.wins,0)}}</span> / <span class="red">${{fmt(x.losses,0)}}</span></td></tr>`).join('');
</script>
"""

out = template[:script_start] + new_script + template[script_end:]
out = out.replace("<title>TrendFrend</title>", "<title>TrendFrend Risk 0.5</title>")
(OUT / "risk05.html").write_text(out, encoding="utf-8")
print("BUILT TRUE RISK05:", OUT / "risk05.html")
