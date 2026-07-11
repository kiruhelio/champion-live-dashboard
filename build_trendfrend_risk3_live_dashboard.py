import csv, json, math, statistics
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
DASH='trendfrend-risk3-live-20260711'
SRC=Path('/home/ubuntu/.hermes/audits/realistic_history_audit_20260711/live_config_atr0_exchange_only/executed_trades.csv')
OUT=ROOT/DASH
DATA=ROOT/'data'/DASH
OUT.mkdir(parents=True, exist_ok=True); DATA.mkdir(parents=True, exist_ok=True)
START=1005.0; RISK=0.03; RESERVE=2.5; LEV=3.0; BUFFER=0.90; MIN_RISK=0.0002
rows=list(csv.DictReader(SRC.open()))
rows.sort(key=lambda r:(float(r['entry_ts']), int(r['idx'])))
equity=START; peak=START; gross_profit=0.0; gross_loss=0.0; wins=losses=0
monthly=defaultdict(lambda:{'profit':0.0,'trades':0,'wins':0,'losses':0,'gp':0.0,'gl':0.0,'start_eq':None,'end_eq':None,'peak':None,'max_dd':0.0})
yearly=defaultdict(lambda:{'profit':0.0,'trades':0,'wins':0,'losses':0,'gp':0.0,'gl':0.0,'start_eq':None,'end_eq':None,'peak':None,'max_dd':0.0})
instr=defaultdict(lambda:{'profit':0.0,'trades':0,'wins':0,'losses':0,'gp':0.0,'gl':0.0})
trade_curve=[]; skipped_min=0
for r in rows:
    month=r['month']; year=month[:4]
    entry=float(r['entry']); sl=float(r['sl']); risk_unit=abs(entry-sl); raw=float(r['raw_pnl_fraction']); sym=r['symbol']
    if risk_unit<=0 or entry<=0: continue
    qty_by_risk=(equity*RISK)/(risk_unit*RESERVE)
    qty_by_margin=(equity*LEV*BUFFER)/(entry*RESERVE)
    qty=min(qty_by_risk, qty_by_margin)
    effective_risk=(qty*RESERVE*risk_unit)/equity if equity>0 else 0
    initial_notional=qty*entry
    if initial_notional<20 or effective_risk<MIN_RISK:
        skipped_min+=1; continue
    pnl=raw*initial_notional
    before=equity
    equity += pnl
    peak=max(peak,equity)
    dd=(peak-equity)/peak*100 if peak>0 else 0
    win=pnl>=0
    if win: wins+=1; gross_profit+=pnl
    else: losses+=1; gross_loss+=abs(pnl)
    for bucket,key in [(monthly,month),(yearly,year)]:
        b=bucket[key]
        if b['start_eq'] is None:
            b['start_eq']=before; b['peak']=before
        b['trades']+=1; b['profit']+=pnl; b['end_eq']=equity; b['peak']=max(b['peak'], equity)
        b['max_dd']=max(b['max_dd'], (b['peak']-equity)/b['peak']*100 if b['peak'] else 0)
        if win: b['wins']+=1; b['gp']+=pnl
        else: b['losses']+=1; b['gl']+=abs(pnl)
    ib=instr[sym]; ib['trades']+=1; ib['profit']+=pnl
    if win: ib['wins']+=1; ib['gp']+=pnl
    else: ib['losses']+=1; ib['gl']+=abs(pnl)
    trade_curve.append({'idx':len(trade_curve)+1,'month':month,'equity':equity,'drawdown_pct':dd,'symbol':sym,'pnl':pnl,'effective_risk_pct':effective_risk*100,'initial_notional':initial_notional})

def pf(gp,gl): return gp/gl if gl>0 else None
def ret(start,end): return (end/start-1)*100 if start else 0
monthly_list=[]; equity_m=[]; dd_m=[]
for m in sorted(monthly):
    b=monthly[m]; r=ret(b['start_eq'], b['end_eq']); p=pf(b['gp'], b['gl']); wr=b['wins']/b['trades']*100 if b['trades'] else 0
    monthly_list.append({'month':m,'return_pct':r,'profit':b['profit'],'trades':b['trades'],'pf':p,'win_rate':wr,'max_dd_pct':b['max_dd'],'start_equity':b['start_eq'],'end_equity':b['end_eq']})
    equity_m.append({'month':m,'equity':b['end_eq']})
    dd_m.append({'month':m,'drawdown_pct':b['max_dd']})
yearly_list=[]
for y in sorted(yearly):
    b=yearly[y]
    yearly_list.append({'year':y,'return_pct':ret(b['start_eq'], b['end_eq']),'profit':b['profit'],'trades':b['trades'],'pf':pf(b['gp'],b['gl']),'win_rate':b['wins']/b['trades']*100 if b['trades'] else 0,'max_dd_pct':b['max_dd'],'start_equity':b['start_eq'],'end_equity':b['end_eq']})
instr_list=[]
for s,b in sorted(instr.items()):
    instr_list.append({'symbol':s,'profit':b['profit'],'trades':b['trades'],'wins':b['wins'],'losses':b['losses'],'pf':pf(b['gp'],b['gl']),'win_rate':b['wins']/b['trades']*100 if b['trades'] else 0})
summary={
  'dashboard':DASH, 'generated_at':datetime.now(timezone.utc).isoformat(), 'source':str(SRC), 'mode':'Current live algorithm: SOL70/NEAR30 3m+1h ATR0 risk3 margin-capped',
  'start_equity':START, 'final_equity':equity, 'return_pct':(equity/START-1)*100, 'profit_factor':pf(gross_profit,gross_loss), 'win_rate':wins/(wins+losses)*100,
  'total_trades':wins+losses, 'wins':wins, 'losses':losses, 'total_months':len(monthly_list), 'positive_months':sum(1 for x in monthly_list if x['return_pct']>0), 'negative_months':sum(1 for x in monthly_list if x['return_pct']<0),
  'avg_monthly_return':statistics.mean([x['return_pct'] for x in monthly_list]), 'median_monthly_return':statistics.median([x['return_pct'] for x in monthly_list]),
  'max_drawdown_pct':max([x['drawdown_pct'] for x in trade_curve] or [0]), 'worst_month_dd_pct':max([x['max_dd_pct'] for x in monthly_list] or [0]),
  'risk_per_trade_pct':3.0, 'risk_reserve_mult':RESERVE, 'leverage':LEV, 'margin_usage_buffer':BUFFER, 'min_effective_risk_pct':MIN_RISK*100, 'skipped_min_effective_or_notional': skipped_min
}
for name,obj in [('summary.json',summary),('monthly.json',monthly_list),('yearly.json',yearly_list),('equity.json',equity_m),('drawdown.json',dd_m),('instruments.json',instr_list),('trade_curve_sample.json', trade_curve[::max(1,len(trade_curve)//1200)])]:
    (DATA/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
html='''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>TrendFrend Risk 3% Live Dashboard</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{--line:rgba(255,255,255,.12);--text:#f5f5f7;--muted:#a1a1aa;--green:#30d158;--red:#ff453a;--blue:#0a84ff;--orange:#ff9f0a}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 16% -8%,rgba(10,132,255,.28),transparent 34%),radial-gradient(circle at 82% 0,rgba(48,209,88,.15),transparent 30%),linear-gradient(180deg,#05070a,#080b12 55%,#05070a);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif}.app{display:grid;grid-template-columns:286px 1fr;min-height:100vh}aside{position:sticky;top:0;height:100vh;padding:28px 20px;border-right:1px solid var(--line);background:rgba(8,12,18,.82);backdrop-filter:blur(18px)}.brand{display:flex;gap:14px;align-items:center;margin-bottom:34px}.logo{width:54px;height:54px;border-radius:16px;background:linear-gradient(145deg,#fff,#b8bec8);color:#05070a;display:grid;place-items:center;font-weight:950;font-size:27px;box-shadow:0 16px 45px rgba(255,255,255,.14)}.brand h1{margin:0;font-size:25px;letter-spacing:-.04em}.brand p{margin:4px 0 0;color:var(--muted);font-size:13px}nav a{display:block;padding:13px 16px;border-radius:16px;color:#d1d5db;text-decoration:none;margin:6px 0}nav a.active{background:rgba(255,255,255,.09);border-left:4px solid var(--green);color:#fff}.side-card{border:1px solid var(--line);border-radius:20px;padding:17px;background:linear-gradient(145deg,rgba(255,255,255,.075),rgba(255,255,255,.035));margin-top:18px}.side-card h3{margin:7px 0;color:var(--green)}.side-card p{color:#c4c8d0;line-height:1.45;font-size:13px}main{padding:30px 36px 44px}.top{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;margin-bottom:18px}.title h2{font-size:44px;letter-spacing:-.06em;margin:0 0 8px}.title p{margin:0;color:#a9b8c7}.badge{font-size:13px;color:var(--green);border:1px solid rgba(48,209,88,.42);border-radius:999px;padding:6px 11px;margin-left:9px;vertical-align:middle}.pill{border:1px solid var(--line);border-radius:999px;padding:12px 18px;background:rgba(255,255,255,.06);white-space:nowrap}.grid{display:grid;gap:14px}.kpis{grid-template-columns:repeat(8,1fr);margin-bottom:14px}.charts{grid-template-columns:1.25fr .75fr;margin-bottom:14px}.lower{grid-template-columns:1fr 1fr;margin-bottom:14px}.bottom{grid-template-columns:1.35fr .65fr}.card{border:1px solid var(--line);border-radius:20px;background:linear-gradient(145deg,rgba(255,255,255,.078),rgba(255,255,255,.035));box-shadow:0 22px 65px rgba(0,0,0,.36);padding:17px;overflow:hidden}.label{color:#c7c7cc;font-size:13px}.value{font-size:25px;font-weight:900;letter-spacing:-.04em;margin:8px 0 5px}.sub{color:var(--muted);font-size:12px;line-height:1.35}.green{color:var(--green)}.red{color:var(--red)}.orange{color:var(--orange)}.section{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.section h3{margin:0}.section span{color:var(--muted);font-size:13px}.chart-card{height:342px}.chart-card canvas{height:265px!important}.mini-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.mini{border:1px solid var(--line);border-radius:15px;padding:13px;background:rgba(0,0,0,.16)}.mini b{display:block;font-size:22px;margin:6px 0}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:var(--muted)}.table-wrap{overflow:auto}.table-wrap table{min-width:980px}.notice{border:1px solid rgba(255,159,10,.42);background:rgba(255,159,10,.08);border-radius:18px;padding:14px;color:#ffd7a0;margin-bottom:14px}@media(max-width:1200px){.app{grid-template-columns:1fr}aside{display:none}.kpis,.charts,.lower,.bottom{grid-template-columns:1fr}.mini-grid{grid-template-columns:1fr 1fr}}
</style></head><body><div class="app"><aside><div class="brand"><div class="logo">T</div><div><h1>TrendFrend</h1><p>Risk 3% Live</p></div></div><nav><a class="active">⌘ Обзор</a><a>↗ Equity</a><a>▦ Monthly</a><a>◎ SOL / NEAR</a><a>⚙ Live Settings</a></nav><div class="side-card"><div class="label">Текущий алгоритм</div><h3>Risk 3% + Margin Cap</h3><p>SOL 70 / NEAR 30<br>3m entry + 1h trend<br>ATR filter 0.0<br>Reserve 2.5x под усреднение<br>Leverage 3x isolated</p></div><div class="side-card"><div class="label">Важно</div><h3>Без Fibonacci</h3><p>Фиксированный риск 3%. Если 3% не помещаются в маржу, qty режется по margin cap. Минимальный effective risk: 0.02%.</p></div></aside><main><div class="top"><div class="title"><h2>TrendFrend <span class="badge">CURRENT LIVE ALGO</span></h2><p>Исторический прогон текущей live-логики: risk 3%, reserve 2.5x, margin cap 90% @ 3x, SOL70/NEAR30, no Fibonacci.</p></div><div class="pill" id="generated">loading…</div></div><div class="notice">Это историческая симуляция текущего sizing поверх reconstructed executed-trades. Реальный live может отличаться из-за fills, проскальзывания, очередности одновременных сигналов и маржи.</div><div class="grid kpis" id="kpis"></div><div class="grid charts"><div class="card chart-card"><div class="section"><h3>Кривая капитала</h3><span id="eq-sub"></span></div><canvas id="eq"></canvas></div><div class="card chart-card"><div class="section"><h3>Просадка</h3><span id="dd-sub"></span></div><canvas id="dd"></canvas></div></div><div class="grid lower"><div class="card"><div class="section"><h3>Помесячная сводка</h3><span id="month-sub"></span></div><div class="mini-grid" id="monthlyMini"></div></div><div class="card"><div class="section"><h3>Инструменты</h3><span>SOL / NEAR</span></div><canvas id="inst" style="height:235px!important"></canvas></div></div><div class="grid bottom"><div class="card"><div class="section"><h3>Помесячная доходность</h3><span>return %, trades, DD</span></div><div class="table-wrap"><table><thead><tr><th>Месяц</th><th>Return</th><th>Profit</th><th>Trades</th><th>PF</th><th>WR</th><th>Max DD</th><th>End Equity</th></tr></thead><tbody id="monthlyRows"></tbody></table></div></div><div class="card"><div class="section"><h3>Годы</h3><span>2021–2026 H1</span></div><table><thead><tr><th>Год</th><th>Return</th><th>Trades</th><th>DD</th></tr></thead><tbody id="yearRows"></tbody></table></div></div></main></div><script>
const BASE="/champion-live-dashboard/data/trendfrend-risk3-live-20260711/";
async function load(f){return fetch(BASE+f+'?v='+Date.now()).then(r=>{if(!r.ok)throw new Error(f+' '+r.status);return r.json()})}
const fmtPct=x=>(x>=0?'+':'−')+Math.abs(x).toLocaleString('en-US',{maximumFractionDigits:2})+'%'; const money=x=>'$'+x.toLocaleString('en-US',{maximumFractionDigits:0}); const cls=x=>x>=0?'green':'red'; const pf=x=>x?x.toFixed(2):'∞';
Promise.all([load('summary.json'),load('monthly.json'),load('yearly.json'),load('equity.json'),load('drawdown.json'),load('instruments.json')]).then(([s,m,y,e,d,ins])=>{
 document.getElementById('generated').textContent='Generated: '+new Date(s.generated_at).toLocaleString();
 const k=[ ['Final Equity',money(s.final_equity),'green','start '+money(s.start_equity)], ['Return',fmtPct(s.return_pct),'green',s.total_months+' months'], ['Max DD',fmtPct(-s.max_drawdown_pct),'red','trade curve'], ['Worst month DD',fmtPct(-s.worst_month_dd_pct),'red','intra-month'], ['PF',pf(s.profit_factor),'green','gross profit / loss'], ['Win Rate',s.win_rate.toFixed(2)+'%','',s.wins+' / '+s.losses], ['Trades',s.total_trades.toLocaleString(),'', 'skipped '+s.skipped_min_effective_or_notional], ['Risk','3.00%','green','reserve 2.5x · cap 3x'] ];
 document.getElementById('kpis').innerHTML=k.map(a=>`<div class="card"><div class="label">${a[0]}</div><div class="value ${a[2]}">${a[1]}</div><div class="sub">${a[3]}</div></div>`).join('');
 document.getElementById('eq-sub').textContent='Final '+money(s.final_equity); document.getElementById('dd-sub').textContent='Max −'+s.max_drawdown_pct.toFixed(2)+'%'; document.getElementById('month-sub').textContent=s.positive_months+'/'+s.total_months+' profitable months';
 const best=m.reduce((a,b)=>a.return_pct>b.return_pct?a:b), worst=m.reduce((a,b)=>a.return_pct<b.return_pct?a:b), worstdd=m.reduce((a,b)=>a.max_dd_pct>b.max_dd_pct?a:b);
 document.getElementById('monthlyMini').innerHTML=[['Avg month',fmtPct(s.avg_monthly_return),'green'],['Median',fmtPct(s.median_monthly_return),'green'],['Best',fmtPct(best.return_pct),'green',best.month],['Worst',fmtPct(worst.return_pct),cls(worst.return_pct),worst.month],['Worst DD',fmtPct(-worstdd.max_dd_pct),'red',worstdd.month],['Positive',s.positive_months+' / '+s.total_months,'green'],['Negative',s.negative_months+' / '+s.total_months,'red'],['Risk floor',s.min_effective_risk_pct.toFixed(2)+'%','orange']].map(a=>`<div class="mini"><span class="label">${a[0]}</span><b class="${a[2]}">${a[1]}</b><span class="sub">${a[3]||''}</span></div>`).join('');
 document.getElementById('monthlyRows').innerHTML=m.map(r=>`<tr><td><b>${r.month}</b></td><td class="${cls(r.return_pct)}">${fmtPct(r.return_pct)}</td><td class="${cls(r.profit)}">${money(r.profit)}</td><td>${r.trades}</td><td>${pf(r.pf)}</td><td>${r.win_rate.toFixed(1)}%</td><td class="red">${fmtPct(-r.max_dd_pct)}</td><td>${money(r.end_equity)}</td></tr>`).join('');
 document.getElementById('yearRows').innerHTML=y.map(r=>`<tr><td><b>${r.year}</b></td><td class="${cls(r.return_pct)}">${fmtPct(r.return_pct)}</td><td>${r.trades}</td><td class="red">${fmtPct(-r.max_dd_pct)}</td></tr>`).join('');
 new Chart(document.getElementById('eq'),{type:'line',data:{labels:e.map(x=>x.month),datasets:[{data:e.map(x=>x.equity),borderColor:'#30d158',backgroundColor:'rgba(48,209,88,.20)',borderWidth:2,tension:.22,pointRadius:0,fill:true}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#8b8f98',maxTicksLimit:8}},y:{grid:{color:'rgba(255,255,255,.08)'},ticks:{color:'#8b8f98'}}}}});
 new Chart(document.getElementById('dd'),{type:'line',data:{labels:d.map(x=>x.month),datasets:[{data:d.map(x=>-x.drawdown_pct),borderColor:'#ff453a',backgroundColor:'rgba(255,69,58,.17)',borderWidth:2,tension:.22,pointRadius:0,fill:true}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#8b8f98',maxTicksLimit:8}},y:{max:0,grid:{color:'rgba(255,255,255,.08)'},ticks:{color:'#8b8f98'}}}}});
 new Chart(document.getElementById('inst'),{type:'doughnut',data:{labels:ins.map(x=>x.symbol),datasets:[{data:ins.map(x=>x.profit),backgroundColor:['#30d158','#0a84ff'],borderWidth:0}]},options:{plugins:{legend:{position:'right',labels:{color:'#c7c7cc'}}},cutout:'58%'}});
}).catch(e=>{document.body.innerHTML='<pre style="color:white;padding:30px">Dashboard load error: '+e+'</pre>'});
</script></body></html>'''
(OUT/'index.html').write_text(html,encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('WROTE', OUT/'index.html', DATA)
