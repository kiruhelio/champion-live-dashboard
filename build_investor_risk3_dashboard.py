import csv, json, math, statistics
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
DASH='investor-risk3-live-20260711'
SRC=Path('/home/ubuntu/.hermes/audits/realistic_history_audit_20260711/live_config_atr0_exchange_only/executed_trades.csv')
OUT=ROOT/DASH
DATA=ROOT/'data'/DASH
OUT.mkdir(parents=True, exist_ok=True); DATA.mkdir(parents=True, exist_ok=True)
START=1005.0; RISK=0.03; RESERVE=2.5; LEV=3.0; BUFFER=0.90; MIN_RISK=0.0002

rows=list(csv.DictReader(SRC.open()))
rows.sort(key=lambda r:(float(r['entry_ts']), int(r['idx'])))

equity=START; peak=START; gross_profit=0.0; gross_loss=0.0; wins=losses=breakevens=0
monthly=defaultdict(lambda:{'profit_n':0.0,'trades':0,'wins':0,'losses':0,'be':0,'gp':0.0,'gl':0.0,'start_eq':None,'end_eq':None,'peak':None,'max_dd':0.0,'by_symbol':defaultdict(lambda:{'profit_n':0.0,'trades':0,'wins':0,'losses':0,'gp':0.0,'gl':0.0})})
yearly=defaultdict(lambda:{'profit_n':0.0,'trades':0,'wins':0,'losses':0,'gp':0.0,'gl':0.0,'start_eq':None,'end_eq':None,'peak':None,'max_dd':0.0,'by_symbol':defaultdict(lambda:{'profit_n':0.0,'trades':0,'wins':0,'losses':0,'gp':0.0,'gl':0.0})})
instr=defaultdict(lambda:{'profit_n':0.0,'trades':0,'wins':0,'losses':0,'gp':0.0,'gl':0.0})
trades_out=[]
durations=[]; risks=[]; rrs=[]; pnls=[]
current_streak_type=None; current_streak_len=0; max_win_streak=0; max_loss_streak=0
best_trade=None; worst_trade=None; skipped_min=0

for r in rows:
    entry=float(r['entry']); sl=float(r['sl']); raw=float(r['raw_pnl_fraction']); sym=r['symbol']; side=r['side']
    month=r['month']; year=month[:4]
    risk_unit=abs(entry-sl)
    if risk_unit<=0 or entry<=0:
        continue
    qty_by_risk=(equity*RISK)/(risk_unit*RESERVE)
    qty_by_margin=(equity*LEV*BUFFER)/(entry*RESERVE)
    qty=min(qty_by_risk, qty_by_margin)
    eff=((qty*RESERVE*risk_unit)/equity) if equity>0 else 0
    initial_notional=qty*entry
    if initial_notional<20 or eff<MIN_RISK:
        skipped_min+=1; continue
    pnl=raw*initial_notional
    rr=None
    tp1=float(r.get('tp1','0') or '0'); tp2=float(r.get('tp2','0') or '0')
    tps=[t for t in [tp1,tp2] if t>0]
    if side=='LONG':
        reward=min((t-entry) for t in tps) if tps else abs(entry-sl)
    else:
        reward=min((entry-t) for t in tps) if tps else abs(entry-sl)
    if risk_unit>0 and reward>0:
        rr=reward/risk_unit
    before=equity
    equity+=pnl; peak=max(peak,equity)
    dd=(peak-equity)/peak*100 if peak>0 else 0
    win=pnl>0; loss=pnl<0; be=abs(pnl)<1e-9
    if win:
        gross_profit+=pnl; wins+=1; current_streak_type='W'; current_streak_len=1 if current_streak_type!='W' else current_streak_len+1; max_win_streak=max(max_win_streak,current_streak_len)
    elif loss:
        gross_loss+=abs(pnl); losses+=1; current_streak_type='L'; current_streak_len=1 if current_streak_type!='L' else current_streak_len+1; max_loss_streak=max(max_loss_streak,current_streak_len)
    else:
        breakevens+=1; current_streak_type=None; current_streak_len=0
    if (win and current_streak_type!='W') or (loss and current_streak_type!='L'):
        current_streak_len=1
    if best_trade is None or pnl>best_trade['pnl']:
        best_trade={'pnl':pnl,'return_pct':raw*100,'symbol':sym,'month':month,'side':side}
    if worst_trade is None or pnl<worst_trade['pnl']:
        worst_trade={'pnl':pnl,'return_pct':raw*100,'symbol':sym,'month':month,'side':side}
    duration=None
    try:
        ent=float(r['entry_ts']); ex=float(r['exit_ts'])
        if ex>ent: duration=ex-ent
    except Exception:
        pass
    pnls.append(raw*100); risks.append(eff*100)
    if rr is not None: rrs.append(rr)
    if duration is not None: durations.append(duration)
    trades_out.append({'idx':len(trades_out)+1,'month':month,'symbol':sym,'side':side,'return_pct':raw*100,'pnl_n':pnl,'duration_sec':duration,'risk_pct':eff*100,'rr':rr})
    for bucket,key in [(monthly,month),(yearly,year)]:
        b=bucket[key]
        if b['start_eq'] is None: b['start_eq']=before; b['peak']=before
        b['trades']+=1; b['profit_n']+=pnl; b['end_eq']=equity; b['peak']=max(b['peak'], equity)
        b['max_dd']=max(b['max_dd'], (b['peak']-equity)/b['peak']*100 if b['peak'] else 0)
        if win: b['wins']+=1; b['gp']+=pnl
        elif loss: b['losses']+=1; b['gl']+=abs(pnl)
        else: b['be']+=1
        bs=b['by_symbol'][sym]; bs['trades']+=1; bs['profit_n']+=pnl
        if win: bs['wins']+=1; bs['gp']+=pnl
        elif loss: bs['losses']+=1; bs['gl']+=abs(pnl)
        else: bs['be']+=1
    ib=instr[sym]; ib['trades']+=1; ib['profit_n']+=pnl; ib['wins']+=wins if False else (ib['wins']+(1 if win else 0)); ib['losses']+=ib['losses']+(1 if loss else 0); ib['be']+=ib['be']+(1 if be else 0)

def pf(gp,gl): return gp/gl if gl>0 else None
def ret(start,end): return (end/start-1)*100 if start else 0
monthly_list=[]; equity_m=[]; dd_m=[]
for m in sorted(monthly):
    b=monthly[m]; r=ret(b['start_eq'], b['end_eq']); p=pf(b['gp'], b['gl']); wr=b['wins']/b['trades']*100 if b['trades'] else 0
    monthly_list.append({'month':m,'return_pct':r,'profit_n':b['profit_n'],'trades':b['trades'],'pf':p,'win_rate':wr,'max_dd_pct':b['max_dd'],'start_equity':b['start_eq'],'end_equity':b['end_eq'],'wins':b['wins'],'losses':b['losses'],'be':b['be']})
    equity_m.append({'month':m,'equity':b['end_eq']})
    dd_m.append({'month':m,'drawdown_pct':b['max_dd']})
yearly_list=[]
for y in sorted(yearly):
    b=yearly[y]; yearly_list.append({'year':y,'return_pct':ret(b['start_eq'], b['end_eq']),'profit_n':b['profit_n'],'trades':b['trades'],'pf':pf(b['gp'],b['gl']),'win_rate':b['wins']/b['trades']*100 if b['trades'] else 0,'max_dd_pct':b['max_dd'],'start_equity':b['start_eq'],'end_equity':b['end_eq'],'wins':b['wins'],'losses':b['losses'],'be':b['be']})
instr_list=[]
for s,b in sorted(instr.items()):
    instr_list.append({'symbol':s,'profit_n':b['profit_n'],'trades':b['trades'],'wins':b['wins'],'losses':b['losses'],'be':b['be'],'pf':pf(b['gp'],b['gl']),'win_rate':b['wins']/b['trades']*100 if b['trades'] else 0})

summary={
  'dashboard':DASH, 'generated_at':datetime.now(timezone.utc).isoformat(), 'source':str(SRC), 'mode':'Investor dashboard: SOL70/NEAR30 risk3 margin-capped current live logic.',
  'start_equity':START, 'final_equity':equity, 'return_pct':(equity/START-1)*100, 'profit_factor':pf(gross_profit,gross_loss), 'win_rate':wins/(wins+losses+breakevens)*100 if (wins+losses+breakevens) else 0,
  'total_trades':wins+losses+breakevens, 'wins':wins, 'losses':losses, 'breakevens':breakevens, 'total_months':len(monthly_list), 'positive_months':sum(1 for x in monthly_list if x['return_pct']>0), 'negative_months':sum(1 for x in monthly_list if x['return_pct']<0),
  'avg_monthly_return':statistics.mean([x['return_pct'] for x in monthly_list]), 'median_monthly_return':statistics.median([x['return_pct'] for x in monthly_list]),
  'max_drawdown_pct':max([x['drawdown_pct'] for x in trades_out] or [0]), 'worst_month_dd_pct':max([x['max_dd_pct'] for x in monthly_list] or [0]),
  'risk_per_trade_pct':3.0, 'margin_usage_buffer':BUFFER, 'leverage':LEV, 'skipped_min_effective_or_notional':skipped_min,
  'avg_trade_duration_hours': statistics.mean(durations)/3600 if durations else None, 'avg_risk_per_trade_pct': statistics.mean(risks) if risks else None, 'avg_rr': statistics.mean(rrs) if rrs else None,
  'best_trade_pct': best_trade['return_pct'] if best_trade else None, 'best_trade': best_trade, 'worst_trade_pct': worst_trade['return_pct'] if worst_trade else None, 'worst_trade': worst_trade,
  'max_win_streak': int(max_win_streak), 'max_loss_streak': int(max_loss_streak),
  'avg_trades_per_month': len(trades_out)/max(1,len(monthly_list)), 'avg_trades_per_day': len(trades_out)/max(1,(trades_out[-1]['idx']-trades_out[0]['idx']+1)) if trades_out else None
}
for name,obj in [('summary.json',summary),('monthly.json',monthly_list),('yearly.json',yearly_list),('equity.json',equity_m),('drawdown.json',dd_m),('instruments.json',instr_list),('trade_curve_sample.json', trades_out[::max(1,len(trades_out)//1200)])]:
    (DATA/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

fmtPct=lambda x: ('' if x is None or math.isinf(x) or math.isnan(x) else (('+' if x>=0 else '−')+f'{abs(x):.2f}%'))
money=lambda x: '$'+f'{x:,.0f}'
cls=lambda x: 'green' if (x is not None and x>=0) else 'red'
pf=lambda x: f'{x:.2f}' if x is not None else '∞'
hms=lambda s: f'{int(s//3600)}h {int((s%3600)//60)}m' if s is not None else 'n/a'

# Build HTML piecewise to avoid quote breakage
parts=[]
parts.append('''<!doctype html><html lang="ru"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>TrendFrend Investor</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{--line:rgba(255,255,255,.12);--text:#f5f5f7;--muted:#a1a1aa;--green:#30d158;--red:#ff453a;--blue:#0a84ff;--orange:#ff9f0a}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at 18% -6%,rgba(10,132,255,.28),transparent 34%),radial-gradient(circle at 82% 2%,rgba(48,209,88,.16),transparent 32%),linear-gradient(180deg,#05070a,#080b12 55%,#05070a);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif}
.app{display:grid;grid-template-columns:264px 1fr;min-height:100vh}
aside{position:sticky;top:0;height:100vh;padding:24px 18px;border-right:1px solid var(--line);background:rgba(8,12,18,.82);backdrop-filter:blur(18px)}
.brand{display:flex;gap:14px;align-items:center;margin-bottom:26px}
.logo{width:48px;height:48px;border-radius:14px;background:linear-gradient(145deg,#fff,#b8bec8);color:#05070a;display:grid;place-items:center;font-weight:950;font-size:24px}
.brand h1{margin:0;font-size:23px}.brand p{margin:3px 0 0;color:var(--muted);font-size:13px}
nav a{display:block;padding:13px 14px;border-radius:16px;color:#d1d5db;text-decoration:none;margin:6px 0}
.side-card{border:1px solid var(--line);border-radius:18px;padding:15px;background:linear-gradient(145deg,rgba(255,255,255,.075),rgba(255,255,255,.035));margin-top:14px}
.side-card h3{margin:7px 0;color:var(--green)}.side-card p{color:#c4c8d0;line-height:1.45;font-size:13px}
main{padding:28px 32px 40px}
.top{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;margin-bottom:18px}
.title h2{font-size:42px;letter-spacing:-.06em;margin:0 0 6px}
.title p{margin:0;color:#a9b8c7}
.badge{font-size:13px;color:var(--green);border:1px solid rgba(48,209,88,.42);border-radius:999px;padding:6px 11px;margin-left:9px;vertical-align:middle}
.pill{border:1px solid var(--line);border-radius:999px;padding:12px 18px;background:rgba(255,255,255,.06);white-space:nowrap}
.grid{display:grid;gap:14px}
.kpis{grid-template-columns:repeat(6,1fr);margin-bottom:14px}
.charts{grid-template-columns:1.2fr .8fr;margin-bottom:14px}
.lower{grid-template-columns:1fr 1fr;margin-bottom:14px}
.bottom{grid-template-columns:1.3fr .7fr}
.card{border:1px solid var(--line);border-radius:20px;background:linear-gradient(145deg,rgba(255,255,255,.078),rgba(255,255,255,.035));box-shadow:0 22px 65px rgba(0,0,0,.36);padding:16px;overflow:hidden}
.label{color:#c7c7cc;font-size:13px}.value{font-size:24px;font-weight:900;letter-spacing:-.04em;margin:7px 0 5px}.sub{color:var(--muted);font-size:12px;line-height:1.35}
.green{color:var(--green)}.red{color:var(--red)}.orange{color:var(--orange)}
.section{display:flex;justify-content:space-between;align-items:center;margin-bottom:11px}.section h3{margin:0;font-size:17px}.section span{color:var(--muted);font-size:13px}
.chart-card{height:330px}.chart-card canvas{height:260px!important}
.mini-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}
.mini{border:1px solid var(--line);border-radius:15px;padding:13px;background:rgba(0,0,0,.15)}
.mini b{display:block;font-size:21px;margin:5px 0}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:var(--muted)}
.table-wrap{overflow:auto}.table-wrap table{min-width:1050px}
.notice{border:1px solid rgba(255,159,10,.42);background:rgba(255,159,10,.08);border-radius:18px;padding:13px;color:#ffd7a0;margin-bottom:14px}
@media(max-width:1200px){.app{grid-template-columns:1fr}aside{display:none}.kpis,.charts,.lower,.bottom{grid-template-columns:1fr}.mini-grid{grid-template-columns:1fr 1fr}}
</style></head><body><div class="app"><aside>
<div class="brand"><div class="logo">TF</div><div><h1>TrendFrend</h1><p>Investor Dashboard</p></div></div>
<nav><a class="active">⌘ Overview</a><a>↗ Equity</a><a>▦ Monthly</a><a>◎ Instruments</a><a>⚙ Settings</a></nav>
<div class="side-card"><div class="label">Mode</div><h3>Risk 3%</h3><p>SOL 70 / NEAR 30<br>3m + 1h<br>No Fibonacci<br>Margin cap 90% @ 3x<br>Reserve 2.5x</p></div>
<div class="side-card"><div class="label">Risk floor</div><h3>Min effective 0.02%</h3><p>Skip tiny notional / micro SL setups</p></div>
</aside><main>
<div class="top"><div class="title"><h2>TrendFrend <span class="badge">INVESTOR VIEW</span></h2><p>SOL70/NEAR30 3m+1h current live sizing, history backtest.</p></div><div class="pill" id="generated">loading…</div></div>
<div class="notice">Historical simulation, not live results. Slip-assumptions and queue-order risk may differ.</div>
<div class="grid kpis" id="kpis"></div>
<div class="grid charts">
<div class="card chart-card"><div class="section"><h3>Equity curve</h3><span id="eq-sub"></span></div><canvas id="eq"></canvas></div>
<div class="card chart-card"><div class="section"><h3>Drawdown</h3><span id="dd-sub"></span></div><canvas id="dd"></canvas></div>
</div>
<div class="grid lower">
<div class="card"><div class="section"><h3>Monthly snapshot</h3><span id="month-sub"></span></div><div class="mini-grid" id="monthlyMini"></div></div>
<div class="card"><div class="section"><h3>Instruments</h3><span>Contribution share</span></div><canvas id="inst" style="height:235px!important"></canvas></div>
</div>
<div class="grid bottom">
<div class="card"><div class="section"><h3>Monthly performance</h3><span>Return % · trades · max DD %</span></div>
<div class="table-wrap"><table><thead><tr><th>Month</th><th>Return</th><th>PF</th><th>WR</th><th>Trades</th><th>W/L/0</th><th>Max DD</th><th>End Equity</th></tr></thead><tbody id="monthlyRows"></tbody></table></div></div>
<div class="card"><div class="section"><h3>Years</h3><span>2021–2026 H1</span></div>
<table><thead><tr><th>Year</th><th>Return</th><th>Trades</th><th>W/L/0</th><th>DD</th></tr></thead><tbody id="yearRows"></tbody></table></div>
<div class="card"><div class="section"><h3>Instrument detail</h3><span>Win · Loss · Breakeven</span></div>
<table><thead><tr><th>Symbol</th><th>Trades</th><th>Return</th><th>WR</th><th>PF</th><th>Win</th><th>Loss</th><th>0</th></tr></thead><tbody id="instrRows"></tbody></table></div>
<div class="card"><div class="section"><h3>T0</h3></div>
</div>
</main></div>
<script>
const BASE="/champion-live-dashboard/data/investor-risk3-live-20260711/";
async function load(f){return fetch(BASE+f+'?v='+Date.now()).then(r=>{if(!r.ok)throw new Error(f+' '+r.status);return r.json()})}
const fmtPct=x=>{if(x===null||x===undefined||mathIs(x))return 'n/a';return (x>=0?'+':'−')+Math.abs(x).toLocaleString('en-US',{maximumFractionDigits:2})+'%'}
function mathIs(x){return Math.isInf(x)||Math.isNaN(x)}
const money=x=>'$'+x.toLocaleString('en-US',{maximumFractionDigits:0}); const cls=x=>x>=0?'green':'red'; const pf=x=>x?x.toFixed(2):'∞'; const hms=s=>{if(!s)return 'n/a';const h=Math.floor(s/3600);const m=Math.floor((s%3600)/60);return h+'h '+m+'m'}; const streak=x=>x?x:'n/a';
Promise.all([load('summary.json'),load('monthly.json'),load('yearly.json'),load('equity.json'),load('drawdown.json'),load('instruments.json')]).then(([s,m,y,e,d,ins])=>{
 document.getElementById('generated').textContent='Generated: '+new Date(s.generated_at).toLocaleString();
 const rows=[
   ['Final Equity',money(s.final_equity),'green','Start '+money(s.start_equity)],
   ['Return',fmtPct(s.return_pct),'green','66 months'],
   ['Max DD',fmtPct(-s.max_drawdown_pct),'red','trade curve'],
   ['Worst month DD',fmtPct(-s.worst_month_dd_pct),'red','intra-month'],
   ['PF',pf(s.profit_factor),'green','gross P/L'],
   ['Win Rate',s.win_rate.toFixed(2)+'%','',s.wins+' / '+s.losses+' / '+s.breakevens],
   ['Trades',s.total_trades.toLocaleString(),'','skipped '+s.skipped_min_effective_or_notional],
   ['Risk',s.risk_per_trade_pct.toFixed(2)+'%','green','margin cap 0.9 · 3x']
 ];
 if(s.avg_trade_duration_hours){rows.push(['Avg duration', (s.avg_trade_duration_hours.toFixed(2))+'h','avg time in trade'])}
 if(s.avg_risk_per_trade_pct){rows.push(['Avg risk/trade', s.avg_risk_per_trade_pct.toFixed(3)+'%','effective after cap'])}
 if(s.avg_rr){rows.push(['Avg R/R', s.avg_rr.toFixed(2),'reward / risk'])}
 if(s.best_trade_pct!==null){rows.push(['Best trade', fmtPct(s.best_trade_pct),'green',s.best_trade.symbol+' '+s.best_trade.side])}
 if(s.worst_trade_pct!==null){rows.push(['Worst trade', fmtPct(s.worst_trade_pct),'red',s.worst_trade.symbol+' '+s.worst_trade.side])}
 if(s.max_win_streak){rows.push(['Longest win streak', streak(s.max_win_streak),'green','consecutive trades'])}
 if(s.max_loss_streak){rows.push(['Longest loss streak', streak(s.max_loss_streak),'red','consecutive trades'])}
 if(s.avg_trades_per_month){rows.push(['Avg trades / month', Math.round(s.avg_trades_per_month),'','trades/mo'])}
 if(s.avg_trades_per_day){rows.push(['Avg trades / day', Math.round(s.avg_trades_per_day),'','trades/day'])}
 document.getElementById('kpis').innerHTML=rows.map(a=>'<div class="card"><div class="label">'+a[0]+'</div><div class="value '+(a[2]||'')+'">'+a[1]+'</div><div class="sub">'+(a[3]||'')+'</div></div>').join('');
 document.getElementById('eq-sub').textContent='Final '+money(s.final_equity);
 document.getElementById('dd-sub').textContent='Max −'+s.max_drawdown_pct.toFixed(2)+'%';
 document.getElementById('month-sub').textContent=s.positive_months+'/'+s.total_months+' profitable months';
 const best=m.reduce((a,b)=>a.return_pct>b.return_pct?a:b), worst=m.reduce((a,b)=>a.return_pct<b.return_pct?a:b), ddworst=m.reduce((a,b)=>a.max_dd_pct>b.max_dd_pct?a:b);
 document.getElementById('monthlyMini').innerHTML=[
   ['Avg month',fmtPct(s.avg_monthly_return),'green'],
   ['Median',fmtPct(s.median_monthly_return),'green'],
   ['Best',fmtPct(best.return_pct),'green',best.month],
   ['Worst',fmtPct(worst.return_pct),cls(worst.return_pct),worst.month],
   ['Worst DD',fmtPct(-ddworst.max_dd_pct),'red',ddworst.month],
   ['Positive',s.positive_months+' / '+s.total_months,'green'],
   ['Negative',s.negative_months+' / '+s.total_months,'red'],
   ['Risk floor',s.min_effective_risk_pct.toFixed(2)+'%','orange']
 ].map(a=>'<div class="mini"><span class="label">'+a[0]+'</span><b class="'+(a[2]||'')+'">'+a[1]+'</b><span class="sub">'+(a[3]||'')+'</span></div>').join('');
 document.getElementById('monthlyRows').innerHTML=m.map(r=>'<tr><td><b>'+r.month+'</b></td><td class="'+cls(r.return_pct)+'">'+fmtPct(r.return_pct)+'</td><td>'+pf(r.pf)+'</td><td>'+r.win_rate.toFixed(1)+'%</td><td>'+r.trades+'</td><td>'+r.wins+' / '+r.losses+' / '+r.be+'</td><td class="red">'+fmtPct(-r.max_dd_pct)+'</td><td>'+money(r.end_equity)+'</td></tr>').join('');
 document.getElementById('yearRows').innerHTML=y.map(r=>'<tr><td><b>'+r.year+'</b></td><td class="'+cls(r.return_pct)+'">'+fmtPct(r.return_pct)+'</td><td>'+r.trades+'</td><td>'+r.wins+' / '+r.losses+' / '+r.be+'</td><td class="red">'+fmtPct(-r.max_dd_pct)+'</td></tr>').join('');
 document.getElementById('instrRows').innerHTML=ins.map(r=>'<tr><td><b>'+r.symbol+'</b></td><td>'+r.trades+'</td><td class="'+cls(r.return_pct)+'">'+fmtPct(r.profit_n?((r.profit_n/s.start_equity)*100 if s.start_equity else 0):0)+'</td><td>'+r.win_rate.toFixed(1)+'%</td><td>'+pf(r.pf)+'</td><td>'+r.wins+'</td><td>'+r.losses+'</td><td>'+r.be+'</td></tr>').join('');
 new Chart(document.getElementById('eq'),{type:'line',data:{labels:e.map(x=>x.month),datasets:[{data:e.map(x=>x.equity),borderColor:'#30d158',backgroundColor:'rgba(48,209,88,.20)',borderWidth:2,tension:.22,pointRadius:0,fill:true}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#8b8f98',maxTicksLimit:8}},y:{grid:{color:'rgba(255,255,255,.08)'},ticks:{color:'#8b8f98'}}}}});
 new Chart(document.getElementById('dd'),{type:'line',data:{labels:d.map(x=>x.month),datasets:[{data:d.map(x=>-x.drawdown_pct),borderColor:'#ff453a',backgroundColor:'rgba(255,69,58,.17)',borderWidth:2,tension:.22,pointRadius:0,fill:true}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#8b8f98',maxTicksLimit:8}},y:{max:0,grid:{color:'rgba(255,255,255,.08)'},ticks:{color:'#8b8f98'}}}}});
 new Chart(document.getElementById('inst'),{type:'doughnut',data:{labels:ins.map(x=>x.symbol),datasets:[{data:ins.map(x=>x.profit_n),backgroundColor:['#30d158','#0a84ff'],borderWidth:0}]},options:{plugins:{legend:{position:'right',labels:{color:'#c7c7cc'}}},cutout:'58%'}});
}).catch(e=>{document.body.innerHTML='<pre style="color:white;padding:30px">Dashboard load error: '+e+'</pre>'});
</script></body></html>'''
parts.append(html)
(OUT/'index.html').write_text(''.join(parts),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('WROTE', OUT/'index.html', DATA)
