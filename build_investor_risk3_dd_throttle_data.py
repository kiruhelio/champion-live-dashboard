import csv, json, statistics
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DASH = 'investor-risk3-live-20260711'
SRC = Path('/home/ubuntu/.hermes/bots/research_near_only_baseline_20260709_181451/out_mm_guards_3pct_20260711_additive/baseline_flat_3pct_additive')
DATA = ROOT / 'data' / DASH
DATA.mkdir(parents=True, exist_ok=True)
BASE_RISK_PCT = 3.0

def dd_cap(dd):
    if dd <= 5.0: return 3.0, 'dd_0_5'
    if dd <= 10.0: return 2.0, 'dd_5_10'
    if dd <= 15.0: return 1.0, 'dd_10_15'
    return 0.5, 'dd_gt_15'

base_rows = list(csv.DictReader((SRC / 'trades_sized.csv').open()))
trades = []
cur_month = None
month_eq = 100.0
month_peak = 100.0
for r in base_rows:
    m = r['month']
    if m != cur_month:
        cur_month = m
        month_eq = 100.0
        month_peak = 100.0
    base_p = float(r['pnl_pct_of_month_start'])
    base_applied = float(r['applied_risk_pct'])
    dd_before = max(0.0, (month_peak - month_eq) / month_peak * 100.0) if month_peak else 0.0
    cap, reason = dd_cap(dd_before)
    applied = min(base_applied, cap)
    pnl_pct = base_p * (applied / base_applied) if base_applied > 0 else 0.0
    before = month_eq
    month_eq += pnl_pct
    month_peak = max(month_peak, month_eq)
    dd_after = max(0.0, (month_peak - month_eq) / month_peak * 100.0) if month_peak else 0.0
    t = dict(r)
    t['pnl_pct_of_month_start'] = f'{pnl_pct:.10f}'
    t['risk_cap_pct'] = f'{cap:.4f}'
    t['applied_risk_pct'] = f'{applied:.4f}'
    t['risk_reason'] = reason
    t['equity_before'] = f'{before:.6f}'
    t['equity_after'] = f'{month_eq:.6f}'
    t['dd_after_pct'] = f'{dd_after:.6f}'
    t['sign'] = '+' if pnl_pct >= 0 else '-'
    trades.append(t)

wins = losses = be = 0
gp = gl = 0.0
instr = defaultdict(lambda: {'return_pct':0.0,'trades':0,'wins':0,'losses':0,'be':0,'gp':0.0,'gl':0.0})
monthly_b = defaultdict(lambda: {'return_pct':0.0,'trades':0,'wins':0,'losses':0,'be':0,'gp':0.0,'gl':0.0,'max_dd_pct':0.0})
yearly_b = defaultdict(lambda: {'return_pct':0.0,'trades':0,'wins':0,'losses':0,'be':0,'gp':0.0,'gl':0.0,'max_dd_pct':0.0})
risks=[]; max_ws=max_ls=cw=cl=0; best=worst=None; sample=[]; cum=peak=0.0
reason_counts=defaultdict(int)
for i,r in enumerate(trades,1):
    pnl=float(r['pnl_pct_of_month_start']); risk=float(r['applied_risk_pct']); risks.append(risk); reason_counts[r['risk_reason']]+=1
    sym=r['symbol']; m=r['month']; y=m[:4]
    win=pnl>0; loss=pnl<0
    if win: wins+=1; gp+=pnl; cw+=1; cl=0; max_ws=max(max_ws,cw)
    elif loss: losses+=1; gl+=abs(pnl); cl+=1; cw=0; max_ls=max(max_ls,cl)
    else: be+=1; cw=cl=0
    for b in (monthly_b[m], yearly_b[y], instr[sym]):
        b['return_pct']+=pnl; b['trades']+=1
        if win: b['wins']+=1; b['gp']+=pnl
        elif loss: b['losses']+=1; b['gl']+=abs(pnl)
        else: b['be']+=1
    monthly_b[m]['max_dd_pct']=max(monthly_b[m]['max_dd_pct'], float(r['dd_after_pct']))
    yearly_b[y]['max_dd_pct']=max(yearly_b[y]['max_dd_pct'], float(r['dd_after_pct']))
    item={'idx':i,'month':m,'symbol':sym,'side':r.get('side',''),'return_pct':pnl,'risk_pct':risk,'risk_reason':r['risk_reason'],'margin_capped':int(r.get('margin_capped') or 0)}
    if best is None or pnl>best['return_pct']: best=dict(item)
    if worst is None or pnl<worst['return_pct']: worst=dict(item)
    cum+=pnl; peak=max(peak,cum); sample.append({'idx':i,'month':m,'equity':cum,'drawdown_pct':max(0,peak-cum),'symbol':sym,'return_pct':pnl,'risk_pct':risk})

def pf(g,l): return g/l if l else None
monthly=[]; equity=[]; drawdown=[]; cum_m=0.0
for m in sorted(monthly_b):
    b=monthly_b[m]; cum_m+=b['return_pct']
    monthly.append({'month':m,'return_pct':b['return_pct'],'trades':b['trades'],'pf':pf(b['gp'],b['gl']),'win_rate':b['wins']/b['trades']*100 if b['trades'] else 0,'max_dd_pct':b['max_dd_pct'],'wins':b['wins'],'losses':b['losses'],'be':b['be']})
    equity.append({'month':m,'equity':cum_m}); drawdown.append({'month':m,'drawdown_pct':b['max_dd_pct']})
yearly=[]
for y in sorted(yearly_b):
    b=yearly_b[y]
    yearly.append({'year':y,'return_pct':b['return_pct'],'trades':b['trades'],'pf':pf(b['gp'],b['gl']),'win_rate':b['wins']/b['trades']*100 if b['trades'] else 0,'max_dd_pct':b['max_dd_pct'],'wins':b['wins'],'losses':b['losses'],'be':b['be']})
instruments=[]
for s,b in sorted(instr.items()):
    instruments.append({'symbol':s,'return_pct':b['return_pct'],'trades':b['trades'],'wins':b['wins'],'losses':b['losses'],'be':b['be'],'pf':pf(b['gp'],b['gl']),'win_rate':b['wins']/b['trades']*100 if b['trades'] else 0})
vals=[x['return_pct'] for x in monthly]
summary={'dashboard':DASH,'generated_at':datetime.now(timezone.utc).isoformat(),'source':str(SRC),'mode':'TrendFrend history: base risk 3% with monthly drawdown throttle only; DD 0-5%=3%, 5-10%=2%, 10-15%=1%, >15%=0.5%.','base_index':100,'equity_index':100+sum(vals),'return_pct':sum(vals),'profit_factor':pf(gp,gl),'win_rate':wins/(wins+losses+be)*100,'total_trades':len(trades),'wins':wins,'losses':losses,'breakevens':be,'total_months':len(monthly),'positive_months':sum(v>0 for v in vals),'negative_months':sum(v<=0 for v in vals),'avg_monthly_return':statistics.mean(vals),'median_monthly_return':statistics.median(vals),'max_drawdown_pct':max(x['max_dd_pct'] for x in monthly),'worst_month_dd_pct':max(x['max_dd_pct'] for x in monthly),'risk_per_trade_pct':3.0,'drawdown_throttle_enabled':True,'dd_throttle_rules':'0-5%: 3%; 5-10%: 2%; 10-15%: 1%; >15%: 0.5%','margin_usage_buffer':0.90,'leverage':3,'skipped_min_effective_or_notional':0,'avg_risk_per_trade_pct':statistics.mean(risks),'min_effective_risk_pct':min(risks),'max_effective_risk_pct':max(risks),'risk_reason_counts':dict(reason_counts),'best_trade_pct':best['return_pct'],'best_trade':best,'worst_trade_pct':worst['return_pct'],'worst_trade':worst,'max_win_streak':max_ws,'max_loss_streak':max_ls,'avg_trades_per_month':len(trades)/len(monthly),'avg_trades_per_day':len(trades)/max(1,365*5.5)}
for name,obj in [('summary.json',summary),('monthly.json',monthly),('yearly.json',yearly),('equity.json',equity),('drawdown.json',drawdown),('instruments.json',instruments),('trade_curve_sample.json',sample[::max(1,len(sample)//1200)])]:
    (DATA/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
