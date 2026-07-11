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

equity=START; peak=START; gp=0.0; gl=0.0; wins=losses=breakevens=0
monthly=defaultdict(lambda:{'profit_n':0.0,'trades':0,'wins':0,'losses':0,'be':0,'gp':0.0,'gl':0.0,'start_eq':None,'end_eq':None,'peak':None,'max_dd':0.0,'by_symbol':defaultdict(lambda:{'profit_n':0.0,'trades':0,'wins':0,'losses':0,'be':0})})
yearly=defaultdict(lambda:{'profit_n':0.0,'trades':0,'wins':0,'losses':0,'be':0,'gp':0.0,'gl':0.0,'start_eq':None,'end_eq':None,'peak':None,'max_dd':0.0,'by_symbol':defaultdict(lambda:{'profit_n':0.0,'trades':0,'wins':0,'losses':0,'be':0})})
instr=defaultdict(lambda:{'profit_n':0.0,'trades':0,'wins':0,'losses':0,'be':0,'gp':0.0,'gl':0.0})
out=[]; durations=[]; risks=[]; rrs=[]; pnls=[]; skipped_min=0
streak_type=None; streak_len=0; max_ws=0; max_ls=0
best=None; worst=None

for r in rows:
    entry=float(r['entry']); sl=float(r['sl']); raw=float(r['raw_pnl_fraction']); sym=r['symbol']; side=r['side']
    month=r['month']; year=month[:4]
    risk_unit=abs(entry-sl)
    if risk_unit<=0 or entry<=0:
        continue
    qty_by_risk=(equity*RISK)/(risk_unit*RESERVE)
    qty_by_margin=(equity*LEV*BUFFER)/(entry*RESERVE)
    qty=min(qty_by_risk, qty_by_margin)
    eff=(qty*RESERVE*risk_unit)/equity if equity>0 else 0
    initial_notional=qty*entry
    if initial_notional<20 or eff<MIN_RISK:
        skipped_min+=1; continue
    pnl=raw*initial_notional
    tp1=float(r.get('tp1','0') or '0'); tp2=float(r.get('tp2','0') or '0')
    tps=[t for t in [tp1,tp2] if t>0]
    if side=='LONG':
        reward=min((t-entry) for t in tps) if tps else abs(entry-sl)
    else:
        reward=min((entry-t) for t in tps) if tps else abs(entry-sl)
    rr=(reward/risk_unit) if risk_unit>0 and reward>0 else None
    before=equity; equity+=pnl; peak=max(peak,equity)
    dd=(peak-equity)/peak*100 if peak>0 else 0
    win=pnl>0; loss=pnl<0; be=abs(pnl)<1e-9
    if win:
        gp+=pnl; wins+=1; streak_type='W'; streak_len=streak_len+1 if streak_type=='W' else 1; max_ws=max(max_ws,streak_len)
    elif loss:
        gl+=abs(pnl); losses+=1; streak_type='L'; streak_len=streak_len+1 if streak_type=='L' else 1; max_ls=max(max_ls,streak_len)
    else:
        breakevens+=1; streak_type=None; streak_len=0
    if win: side_sym='win'
    elif loss: side_sym='loss'
    else: side_sym='be'
    if best is None or pnl>best['pnl']: best={'pnl':pnl,'return_pct':raw*100,'symbol':sym,'month':month,'side':side}
    if worst is None or pnl<worst['pnl']: worst={'pnl':pnl,'return_pct':raw*100,'symbol':sym,'month':month,'side':side}
    duration=None
    try:
        ent=float(r['entry_ts']); ex=float(r['exit_ts'])
        if ex>ent: duration=ex-ent
    except Exception:
        pass
    pnls.append(raw*100); risks.append(eff*100)
    if rr is not None: rrs.append(rr)
    if duration is not None: durations.append(duration)
    out.append({'month':month,'symbol':sym,'side':side,'return_pct':raw*100,'pnl_n':pnl,'duration_sec':duration,'risk_pct':eff*100,'rr':rr})

    for bucket,key in [(monthly,month),(yearly,year)]:
        b=bucket[key]
        if b['start_eq'] is None: b['start_eq']=before; b['peak']=before
        b['trades']+=1; b['profit_n']+=pnl; b['end_eq']=equity; b['peak']=max(b['peak'],equity)
        b['max_dd']=max(b['max_dd'], (b['peak']-equity)/b['peak']*100 if b['peak'] else 0)
        if win: b['wins']+=1; b['gp']+=pnl
        elif loss: b['losses']+=1; b['gl']+=abs(pnl)
        else: b['be']+=1
        bs=b['by_symbol'][sym]; bs['trades']+=1; bs['profit_n']+=pnl
        if win: bs['wins']+=1
        elif loss: bs['losses']+=1
        else: bs['be']+=1
    ib=instr[sym]; ib['trades']+=1; ib['profit_n']+=pnl
    if win: ib['wins']+=1; ib['gp']+=pnl
    elif loss: ib['losses']+=1; ib['gl']+=abs(pnl)
    else: ib['be']+=1

def pf_f(gp,gl): return gp/gl if gl>0 else None
def ret_f(start,end): return (end/start-1)*100 if start else 0
monthly_list=[]; equity_m=[]; dd_m=[]
for m in sorted(monthly):
    b=monthly[m]; r=ret_f(b['start_eq'], b['end_eq']); p=pf_f(b['gp'], b['gl']); wr=b['wins']/b['trades']*100 if b['trades'] else 0
    monthly_list.append({'month':m,'return_pct':r,'profit_n':b['profit_n'],'trades':b['trades'],'pf':p,'win_rate':wr,'max_dd_pct':b['max_dd'],'start_equity':b['start_eq'],'end_equity':b['end_eq'],'wins':b['wins'],'losses':b['losses'],'be':b['be']})
    equity_m.append({'month':m,'equity':b['end_eq']})
    dd_m.append({'month':m,'drawdown_pct':b['max_dd']})
yearly_list=[]
for y in sorted(yearly):
    b=yearly[y]; yearly_list.append({'year':y,'return_pct':ret_f(b['start_eq'], b['end_eq']),'profit_n':b['profit_n'],'trades':b['trades'],'pf':pf_f(b['gp'],b['gl']),'win_rate':b['wins']/b['trades']*100 if b['trades'] else 0,'max_dd_pct':b['max_dd'],'start_equity':b['start_eq'],'end_equity':b['end_eq'],'wins':b['wins'],'losses':b['losses'],'be':b['be']})
instr_list=[]
for s,b in sorted(instr.items()):
    instr_list.append({'symbol':s,'profit_n':b['profit_n'],'trades':b['trades'],'wins':b['wins'],'losses':b['losses'],'be':b['be'],'pf':pf_f(b['gp'],b['gl']),'win_rate':b['wins']/b['trades']*100 if b['trades'] else 0})
summary={
  'dashboard':DASH, 'generated_at':datetime.now(timezone.utc).isoformat(), 'source':str(SRC), 'mode':'Investor dashboard: SOL70/NEAR30 risk3 margin-capped current live logic.',
  'start_equity':START, 'final_equity':equity, 'return_pct':(equity/START-1)*100, 'profit_factor':pf_f(gp,gl), 'win_rate':wins/(wins+losses+breakevens)*100 if (wins+losses+breakevens) else 0,
  'total_trades':wins+losses+breakevens, 'wins':wins, 'losses':losses, 'breakevens':breakevens, 'total_months':len(monthly_list), 'positive_months':sum(1 for x in monthly_list if x['return_pct']>0), 'negative_months':sum(1 for x in monthly_list if x['return_pct']<0),
  'avg_monthly_return':statistics.mean([x['return_pct'] for x in monthly_list]), 'median_monthly_return':statistics.median([x['return_pct'] for x in monthly_list]),
  'max_drawdown_pct': max((x['drawdown_pct'] for x in dd_m), default=0), 'worst_month_dd_pct': max((x['max_dd_pct'] for x in monthly_list), default=0),
  'risk_per_trade_pct':3.0, 'margin_usage_buffer':BUFFER, 'leverage':LEV, 'skipped_min_effective_or_notional':skipped_min,
  'avg_trade_duration_hours': (statistics.mean(durations)/3600) if durations else None, 'avg_risk_per_trade_pct': (statistics.mean(risks)) if risks else None, 'avg_rr': (statistics.mean(rrs)) if rrs else None,
  'best_trade_pct': best['return_pct'] if best else None, 'best_trade': best, 'worst_trade_pct': worst['return_pct'] if worst else None, 'worst_trade': worst,
  'max_win_streak': int(max_ws), 'max_loss_streak': int(max_ls),
  'avg_trades_per_month': len(out)/max(1,len(monthly_list))
 }
first_ts=last_ts=None
if rows:
    try:
        first_ts=float(rows[0]['entry_ts']); last_ts=float(rows[-1]['exit_ts'])
    except Exception:
        first_ts=last_ts=None
days_span = max(1,(last_ts-first_ts)/86400) if first_ts is not None and last_ts else max(1,len(monthly_list)*30)
summary['avg_trades_per_day'] = len(out)/days_span
for name,obj in [('summary.json',summary),('monthly.json',monthly_list),('yearly.json',yearly_list),('equity.json',equity_m),('drawdown.json',dd_m),('instruments.json',instr_list),('trade_curve_sample.json', out[::max(1,len(out)//1200)])]:
    (DATA/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
print('WROTE JSON for', DASH)
