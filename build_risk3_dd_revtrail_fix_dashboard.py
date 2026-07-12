#!/usr/bin/env python3
import csv, json, math, statistics
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DASH = 'risk3-dd-revtrail-fix-20260712'
SRC = Path('/home/ubuntu/.hermes/bots/research_near_only_baseline_20260709_181451/out_current_dd_throttle_per_trade_compound_revtrail_fix_20260712')
ADD_SRC = Path('/home/ubuntu/.hermes/bots/research_near_only_baseline_20260709_181451/out_mm_guards_3pct_20260711_additive_revtrail_fix/baseline_flat_3pct_additive')
CMP = SRC / 'comparison_old_vs_revtrail_fix.json'
OUT = ROOT / DASH
DATA = ROOT / 'data' / DASH
OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

def read_csv(p):
    with p.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def fnum(x, default=0.0):
    if x is None or x == '': return default
    return float(x)

summary_src = json.loads((SRC / 'summary.json').read_text(encoding='utf-8'))
comparison = json.loads(CMP.read_text(encoding='utf-8')) if CMP.exists() else {}
monthly_src = read_csv(SRC / 'monthly.csv')
yearly_src = read_csv(SRC / 'yearly.csv')
instr_src = read_csv(SRC / 'instruments.csv')
trades_src = read_csv(SRC / 'trades_compounded.csv')
add_summary = json.loads((ADD_SRC / 'summary.json').read_text(encoding='utf-8'))

# Monthly JSON for dashboard and verification contract
monthly = []
equity = []
drawdown = []
log10_eq = math.log10(1000.0)
for r in monthly_src:
    ret = fnum(r['return_pct'])
    factor = max(1e-12, 1.0 + ret / 100.0)
    log10_eq += math.log10(factor)
    item = {
        'month': r['month'],
        'return_pct': ret,
        'profit': ret,
        'trades': int(float(r['trades'])),
        'wins': int(float(r['wins'])),
        'losses': int(float(r['losses'])),
        'be': 0,
        'pf': fnum(r['profit_factor_fractional'], None),
        'win_rate': fnum(r['win_rate_pct']),
        'max_dd_pct': fnum(r['max_dd_pct']),
        'avg_risk_pct': fnum(r['avg_risk_pct']),
        'risk_dd_0_5': int(float(r.get('risk_dd_0_5') or 0)),
        'risk_dd_5_10': int(float(r.get('risk_dd_5_10') or 0)),
        'risk_dd_10_15': int(float(r.get('risk_dd_10_15') or 0)),
        'risk_dd_gt_15': int(float(r.get('risk_dd_gt_15') or 0)),
        'log10_equity': log10_eq,
    }
    monthly.append(item)
    equity.append({'month': r['month'], 'equity': log10_eq, 'log10_equity': log10_eq})
    drawdown.append({'month': r['month'], 'drawdown_pct': item['max_dd_pct']})

yearly = []
for r in yearly_src:
    yearly.append({
        'year': r['year'],
        'return_pct': fnum(r['return_pct']),
        'trades': int(float(r['trades'])),
        'wins': int(float(r['wins'])),
        'losses': int(float(r['losses'])),
        'be': 0,
        'pf': fnum(r['profit_factor_fractional'], None),
        'win_rate': fnum(r['win_rate_pct']),
        'max_dd_pct': fnum(r['max_month_dd_pct']),
    })

instruments = []
for r in instr_src:
    instruments.append({
        'symbol': r['symbol'],
        'trades': int(float(r['trades'])),
        'wins': int(float(r['wins'])),
        'losses': int(float(r['losses'])),
        'be': 0,
        'win_rate': fnum(r['win_rate_pct']),
        'pf': fnum(r['profit_factor_fractional'], None),
        'log_growth_contribution': fnum(r['log_growth_contribution']),
    })

# Sample trade curve for scatter/curve: keep about 1500 points
sample_step = max(1, len(trades_src) // 1500)
trade_curve = []
for r in trades_src[::sample_step]:
    trade_curve.append({
        'idx': int(float(r['idx'])),
        'month': r['month'],
        'symbol': r['symbol'],
        'pnl_pct': fnum(r['pnl_pct_of_equity_before']),
        'applied_risk_pct': fnum(r['applied_risk_pct']),
        'month_dd_after_pct': fnum(r['month_dd_after_pct']),
        'global_dd_after_pct': fnum(r['global_dd_after_pct']),
        'log10_equity_after': fnum(r['log_equity_after']) / math.log(10),
        'risk_reason': r['risk_reason'],
    })

vals = [m['return_pct'] for m in monthly]
summary = {
    'dashboard': DASH,
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'source': str(SRC),
    'mode': 'Corrected reverse-trailing sign fix; live current model: SOL/NEAR, 3m+1h, ATR=0, flat 3% per instrument, monthly DD throttle only, per-trade compounding.',
    'start_equity': 1000.0,
    'final_equity': summary_src.get('final_equity'),
    'final_equity_log10': summary_src.get('final_equity_log10'),
    'final_equity_scientific': summary_src.get('final_equity_scientific'),
    'return_pct': add_summary.get('sum_monthly_return_pct'),
    'return_pct_label': 'bounded additive monthly return from corrected 3% baseline source',
    'compounded_return_pct_scientific': summary_src.get('total_return_pct_scientific'),
    'profit_factor': summary_src.get('profit_factor_fractional'),
    'win_rate': summary_src.get('win_rate_pct'),
    'total_trades': summary_src.get('total_trades'),
    'wins': summary_src.get('wins'),
    'losses': summary_src.get('losses'),
    'breakevens': summary_src.get('breakevens'),
    'total_months': len(monthly),
    'positive_months': summary_src.get('profitable_months'),
    'negative_months': summary_src.get('unprofitable_months'),
    'avg_monthly_return': summary_src.get('avg_monthly_return_pct'),
    'median_monthly_return': summary_src.get('median_monthly_return_pct'),
    'best_month_pct': max(vals),
    'worst_month_pct': min(vals),
    'max_drawdown_pct': summary_src.get('max_global_drawdown_pct'),
    'worst_month_dd_pct': summary_src.get('max_monthly_dd_pct'),
    'risk_per_trade_pct': 3.0,
    'drawdown_throttle_enabled': True,
    'dd_throttle_rules': 'Monthly DD: 0-5%=3%, 5-10%=2%, 10-15%=1%, >15%=0.5%',
    'margin_usage_buffer': 0.90,
    'leverage': 3,
    'avg_risk_per_trade_pct': summary_src.get('avg_applied_risk_pct'),
    'min_effective_risk_pct': summary_src.get('min_applied_risk_pct'),
    'max_effective_risk_pct': summary_src.get('max_applied_risk_pct'),
    'risk_reason_counts': summary_src.get('risk_reason_counts'),
    'best_trade_pct': summary_src.get('best_trade_pct_of_equity_before'),
    'best_trade': summary_src.get('best_trade'),
    'worst_trade_pct': summary_src.get('worst_trade_pct_of_equity_before'),
    'worst_trade': summary_src.get('worst_trade'),
    'max_win_streak': summary_src.get('max_win_streak'),
    'max_loss_streak': summary_src.get('max_loss_streak'),
    'avg_trades_per_month': summary_src.get('total_trades') / len(monthly),
    'old_vs_new': comparison,
}

for name, obj in [
    ('summary.json', summary), ('monthly.json', monthly), ('yearly.json', yearly),
    ('equity.json', equity), ('drawdown.json', drawdown), ('instruments.json', instruments),
    ('trade_curve_sample.json', trade_curve)
]:
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

html = f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TrendFrend Risk3 DD RevTrail Fix</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{{--bg:#05070b;--panel:rgba(255,255,255,.075);--panel2:rgba(255,255,255,.04);--line:rgba(255,255,255,.12);--txt:#f5f7fb;--mut:#9ca3af;--green:#30d158;--red:#ff453a;--blue:#0a84ff;--orange:#ff9f0a;--violet:#bf5af2}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 15% -5%,rgba(10,132,255,.28),transparent 32%),radial-gradient(circle at 80% 0,rgba(48,209,88,.16),transparent 30%),linear-gradient(180deg,#05070b,#0a0f19 60%,#05070b);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif}}
.app{{display:grid;grid-template-columns:280px 1fr;min-height:100vh}} aside{{position:sticky;top:0;height:100vh;padding:24px 18px;border-right:1px solid var(--line);background:rgba(5,7,11,.76);backdrop-filter:blur(20px)}}
.logo{{width:52px;height:52px;border-radius:16px;background:linear-gradient(145deg,#fff,#b8c2d8);color:#05070b;display:grid;place-items:center;font-weight:950;font-size:24px}} .brand{{display:flex;gap:13px;align-items:center;margin-bottom:25px}} h1{{font-size:23px;margin:0}} .brand p, .mut{{color:var(--mut);margin:3px 0 0;font-size:13px}}
.side{{border:1px solid var(--line);border-radius:18px;padding:15px;margin:12px 0;background:linear-gradient(145deg,var(--panel),var(--panel2))}} .side h3{{margin:5px 0;color:var(--green)}} .side p{{color:#cbd5e1;font-size:13px;line-height:1.45}}
main{{padding:28px 32px 42px}} .top{{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:16px}} h2{{font-size:42px;letter-spacing:-.055em;margin:0}} .badge{{font-size:13px;color:var(--green);border:1px solid rgba(48,209,88,.45);border-radius:999px;padding:6px 10px;vertical-align:middle}} .pill{{border:1px solid var(--line);border-radius:999px;padding:10px 15px;background:rgba(255,255,255,.06);white-space:nowrap;color:#dbeafe}}
.notice{{border:1px solid rgba(255,159,10,.42);background:rgba(255,159,10,.08);border-radius:18px;padding:13px;color:#ffd7a0;margin:12px 0 16px}}
.grid{{display:grid;gap:14px}} .kpis{{grid-template-columns:repeat(6,1fr)}} .charts{{grid-template-columns:1.25fr .75fr;margin-top:14px}} .two{{grid-template-columns:1fr 1fr;margin-top:14px}} .card{{border:1px solid var(--line);border-radius:20px;background:linear-gradient(145deg,var(--panel),var(--panel2));box-shadow:0 22px 65px rgba(0,0,0,.34);padding:16px;overflow:hidden}} .label{{color:#c7c7cc;font-size:13px}} .value{{font-size:25px;font-weight:900;letter-spacing:-.04em;margin:6px 0 4px}} .sub{{color:var(--mut);font-size:12px;line-height:1.35}} .green{{color:var(--green)}} .red{{color:var(--red)}} .orange{{color:var(--orange)}} .blue{{color:var(--blue)}} .violet{{color:var(--violet)}}
.section{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}} .section h3{{margin:0;font-size:17px}} .section span{{color:var(--mut);font-size:13px}} .chart-card{{height:330px}} .chart-card canvas{{height:260px!important}}
.mini-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}} .mini{{border:1px solid var(--line);border-radius:15px;padding:12px;background:rgba(0,0,0,.15)}} .mini b{{display:block;font-size:20px;margin:4px 0}}
table{{width:100%;border-collapse:collapse;font-size:13px}} th,td{{padding:8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}} th:first-child,td:first-child{{text-align:left}} th{{color:var(--mut)}} .table-wrap{{overflow:auto;max-height:470px}} .table-wrap table{{min-width:980px}}
@media(max-width:1200px){{.app{{grid-template-columns:1fr}} aside{{display:none}} .kpis,.charts,.two{{grid-template-columns:1fr}} .mini-grid{{grid-template-columns:1fr 1fr}}}}
</style></head><body><div class="app"><aside>
<div class="brand"><div class="logo">TF</div><div><h1>TrendFrend</h1><p>Corrected 3% Dashboard</p></div></div>
<div class="side"><div class="label">Model</div><h3>3% per instrument</h3><p>FLAT SOL/NEAR risk<br>3m + 1h, ATR=0<br>TP1=1R / TP2=4.5R<br>Averaging on, max add=1</p></div>
<div class="side"><div class="label">Smooth risk</div><h3>Monthly DD throttle</h3><p>0–5% DD → 3%<br>5–10% → 2%<br>10–15% → 1%<br>&gt;15% → 0.5%</p></div>
<div class="side"><div class="label">Fix</div><h3>RevTrail sign fixed</h3><p>Reverse trailing after TP1 PnL sign corrected. Dashboard uses regenerated corrected source, not stale CSV.</p></div>
</aside><main>
<div class="top"><div><h2>Risk3 DD Throttle <span class="badge">REVTRAIL FIX</span></h2><p class="mut">Visual full-history dashboard · corrected backtest engine · bounded + compounded metrics.</p></div><div class="pill" id="generated">loading…</div></div>
<div class="notice">Full-history compounding over 40,386 trades is mathematically explosive. Main decision metrics: PF, win rate, drawdown, monthly distribution, 2026 bounded period, and log10 equity curve.</div>
<div class="grid kpis" id="kpis"></div>
<div class="grid charts"><div class="card chart-card"><div class="section"><h3>Compounded equity curve</h3><span>log10 equity, start 1000</span></div><canvas id="eq"></canvas></div><div class="card chart-card"><div class="section"><h3>Monthly drawdown</h3><span id="ddSub"></span></div><canvas id="dd"></canvas></div></div>
<div class="grid two"><div class="card"><div class="section"><h3>Monthly snapshot</h3><span id="mSub"></span></div><div class="mini-grid" id="mini"></div></div><div class="card"><div class="section"><h3>Risk throttle usage</h3><span>trade count by DD bucket</span></div><canvas id="risk"></canvas></div></div>
<div class="grid two"><div class="card"><div class="section"><h3>Old vs corrected</h3><span>before/after sign fix</span></div><div class="mini-grid" id="delta"></div></div><div class="card"><div class="section"><h3>Instrument detail</h3><span>SOL vs NEAR</span></div><table><thead><tr><th>Symbol</th><th>Trades</th><th>WR</th><th>PF</th><th>Log growth</th></tr></thead><tbody id="instRows"></tbody></table></div></div>
<div class="grid two"><div class="card"><div class="section"><h3>Monthly performance</h3><span>return · PF · WR · DD</span></div><div class="table-wrap"><table><thead><tr><th>Month</th><th>Return</th><th>PF</th><th>WR</th><th>Trades</th><th>W/L</th><th>DD</th><th>Avg risk</th></tr></thead><tbody id="monthRows"></tbody></table></div></div><div class="card"><div class="section"><h3>Yearly performance</h3><span>2021–2026</span></div><table><thead><tr><th>Year</th><th>Return</th><th>PF</th><th>WR</th><th>Trades</th><th>DD</th></tr></thead><tbody id="yearRows"></tbody></table></div></div>
</main></div><script>
const BASE='/champion-live-dashboard/data/{DASH}/';
async function load(f){{const r=await fetch(BASE+f+'?v='+Date.now()); if(!r.ok) throw new Error(f+' '+r.status); return r.json();}}
const pct=x=>{{if(x===null||x===undefined||!isFinite(x))return 'n/a'; const ax=Math.abs(x); const s=x>=0?'+':'−'; if(ax>=1e6)return s+ax.toExponential(2)+'%'; return s+ax.toLocaleString('en-US',{{maximumFractionDigits:2}})+'%';}};
const num=x=>x.toLocaleString('en-US',{{maximumFractionDigits:2}}); const pf=x=>x?Number(x).toFixed(2):'∞'; const cls=x=>x>=0?'green':'red';
Promise.all([load('summary.json'),load('monthly.json'),load('yearly.json'),load('equity.json'),load('drawdown.json'),load('instruments.json'),load('trade_curve_sample.json')]).then(([s,m,y,e,d,ins,tc])=>{{
 document.getElementById('generated').textContent='Generated: '+new Date(s.generated_at).toLocaleString();
 const old=s.old_vs_new||{{}}; const oldDD=old.old_dd_compound||{{}}; const newDD=old.new_dd_compound||{{}}; const changed=(old.changed_raw_trades||{{}});
 const kpis=[['Trades',s.total_trades.toLocaleString(),'','corrected source'],['Win rate',num(s.win_rate)+'%','green',s.wins+' / '+s.losses],['PF',pf(s.profit_factor),'green','fractional returns'],['Max DD',pct(-s.max_drawdown_pct),'red','global/monthly'],['Avg risk',num(s.avg_risk_per_trade_pct)+'%','orange','after DD throttle'],['Worst month',pct(s.worst_month_pct),'red','only losing month'],['Additive return',pct(s.return_pct),'green','bounded baseline metric'],['Final equity',s.final_equity_scientific,'violet','compounded artifact'],['Log10 final',num(s.final_equity_log10),'blue','plot scale'],['Best trade',pct(s.best_trade_pct),'green',s.best_trade?.symbol||''],['Worst trade',pct(s.worst_trade_pct),'red',s.worst_trade?.symbol||''],['Changed PnL',changed.changed_pnl?.toLocaleString()||'n/a','orange',(changed.neg_to_pos||0)+' neg→pos']];
 document.getElementById('kpis').innerHTML=kpis.map(a=>`<div class="card"><div class="label">${{a[0]}}</div><div class="value ${{a[2]}}">${{a[1]}}</div><div class="sub">${{a[3]}}</div></div>`).join('');
 const best=m.reduce((a,b)=>a.return_pct>b.return_pct?a:b), worst=m.reduce((a,b)=>a.return_pct<b.return_pct?a:b), ddworst=m.reduce((a,b)=>a.max_dd_pct>b.max_dd_pct?a:b);
 document.getElementById('ddSub').textContent='Max −'+num(s.max_drawdown_pct)+'%'; document.getElementById('mSub').textContent=s.positive_months+'/'+s.total_months+' profitable months';
 const minis=[['Avg month',pct(s.avg_monthly_return),'green'],['Median',pct(s.median_monthly_return),'green'],['Best',pct(best.return_pct),'green',best.month],['Worst',pct(worst.return_pct),cls(worst.return_pct),worst.month],['Worst DD',pct(-ddworst.max_dd_pct),'red',ddworst.month],['Positive',s.positive_months+' / '+s.total_months,'green'],['Max win streak',s.max_win_streak,'green'],['Max loss streak',s.max_loss_streak,'red']];
 document.getElementById('mini').innerHTML=minis.map(a=>`<div class="mini"><span class="label">${{a[0]}}</span><b class="${{a[2]||''}}">${{a[1]}}</b><span class="sub">${{a[3]||''}}</span></div>`).join('');
 const deltas=[['WR',num(oldDD.win_rate_pct||0)+' → '+num(newDD.win_rate_pct||0)+'%','green'],['PF',pf(oldDD.profit_factor_fractional)+' → '+pf(newDD.profit_factor_fractional),'green'],['Max DD',num(oldDD.max_global_drawdown_pct||0)+' → '+num(newDD.max_global_drawdown_pct||0)+'%','green'],['Final log',oldDD.final_equity_scientific+' → '+newDD.final_equity_scientific,'violet']];
 document.getElementById('delta').innerHTML=deltas.map(a=>`<div class="mini"><span class="label">${{a[0]}}</span><b class="${{a[2]}}">${{a[1]}}</b></div>`).join('');
 document.getElementById('monthRows').innerHTML=m.map(r=>`<tr><td><b>${{r.month}}</b></td><td class="${{cls(r.return_pct)}}">${{pct(r.return_pct)}}</td><td>${{pf(r.pf)}}</td><td>${{num(r.win_rate)}}%</td><td>${{r.trades}}</td><td>${{r.wins}} / ${{r.losses}}</td><td class="red">${{pct(-r.max_dd_pct)}}</td><td>${{num(r.avg_risk_pct)}}%</td></tr>`).join('');
 document.getElementById('yearRows').innerHTML=y.map(r=>`<tr><td><b>${{r.year}}</b></td><td class="${{cls(r.return_pct)}}">${{pct(r.return_pct)}}</td><td>${{pf(r.pf)}}</td><td>${{num(r.win_rate)}}%</td><td>${{r.trades}}</td><td class="red">${{pct(-r.max_dd_pct)}}</td></tr>`).join('');
 document.getElementById('instRows').innerHTML=ins.map(r=>`<tr><td><b>${{r.symbol}}</b></td><td>${{r.trades}}</td><td>${{num(r.win_rate)}}%</td><td>${{pf(r.pf)}}</td><td>${{num(r.log_growth_contribution)}}</td></tr>`).join('');
 const grid={{color:'rgba(255,255,255,.08)'}}, tick={{color:'#9ca3af'}};
 new Chart(document.getElementById('eq'),{{type:'line',data:{{labels:e.map(x=>x.month),datasets:[{{data:e.map(x=>x.equity),borderColor:'#30d158',backgroundColor:'rgba(48,209,88,.18)',fill:true,borderWidth:2,tension:.22,pointRadius:0}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}},ticks:tick}},y:{{grid:grid,ticks:tick,title:{{display:true,text:'log10 equity',color:'#9ca3af'}}}}}}}}}});
 new Chart(document.getElementById('dd'),{{type:'line',data:{{labels:d.map(x=>x.month),datasets:[{{data:d.map(x=>-x.drawdown_pct),borderColor:'#ff453a',backgroundColor:'rgba(255,69,58,.17)',fill:true,borderWidth:2,tension:.22,pointRadius:0}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}},ticks:tick}},y:{{max:0,grid:grid,ticks:tick}}}}}}}});
 const rc=s.risk_reason_counts||{{}}; new Chart(document.getElementById('risk'),{{type:'doughnut',data:{{labels:['0–5% DD','5–10% DD','10–15% DD','>15% DD'],datasets:[{{data:[rc.dd_0_5||0,rc.dd_5_10||0,rc.dd_10_15||0,rc.dd_gt_15||0],backgroundColor:['#30d158','#0a84ff','#ff9f0a','#ff453a'],borderWidth:0}}]}},options:{{plugins:{{legend:{{position:'right',labels:{{color:'#c7c7cc'}}}}}},cutout:'58%'}}}});
}}).catch(e=>{{document.body.innerHTML='<pre style="color:white;padding:30px">Dashboard load error: '+e.stack+'</pre>'; console.error(e);}});
</script></body></html>'''
(OUT / 'index.html').write_text(html, encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
print('WROTE', OUT / 'index.html')
print('DATA', DATA)
