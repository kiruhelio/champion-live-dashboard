#!/usr/bin/env python3
import csv, json, math, statistics
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

ROOT = Path(__file__).resolve().parent
DASH = 'risk3-dd-revtrail-fix-20260712'
RESEARCH = Path('/home/ubuntu/.hermes/bots/research_near_only_baseline_20260709_181451')
COMP_SRC = RESEARCH / 'out_current_dd_throttle_per_trade_compound_revtrail_fix_20260712'
ADD_SRC = RESEARCH / 'out_mm_guards_3pct_20260711_additive_revtrail_fix' / 'baseline_flat_3pct_additive'
RAW_SRC = RESEARCH / 'out_dynamic_risk_currentsettings_revtrail_fix' / 'fixed_3pct_flat' / 'trades.csv'
CMP = COMP_SRC / 'comparison_old_vs_revtrail_fix.json'
OUT = ROOT / DASH
DATA = ROOT / 'data' / DASH
OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)


def read_csv(p: Path):
    with p.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def fnum(x, default=0.0):
    if x is None or x == '':
        return default
    return float(x)


def safe_pf(gp, gl):
    return gp / gl if gl > 0 else None

add_summary = json.loads((ADD_SRC / 'summary.json').read_text(encoding='utf-8'))
comp_summary = json.loads((COMP_SRC / 'summary.json').read_text(encoding='utf-8'))
comparison = json.loads(CMP.read_text(encoding='utf-8')) if CMP.exists() else {}
add_monthly_src = read_csv(ADD_SRC / 'monthly.csv')
add_yearly_src = read_csv(ADD_SRC / 'yearly.csv')
add_trades = read_csv(ADD_SRC / 'trades_sized.csv')
raw_trades = read_csv(RAW_SRC)
raw_trades.sort(key=lambda r: (float(r.get('entry_ts') or r.get('exit_ts') or 0), r.get('symbol', '')))

if len(raw_trades) != len(add_trades):
    raise SystemExit(f'trade count mismatch raw={len(raw_trades)} add={len(add_trades)}')

# Main dashboard metrics are monthly-reset additive, NOT per-trade compounded.
monthly = []
equity = []
drawdown = []
illustrative_equity = 1000.0
for r in add_monthly_src:
    ret = fnum(r['return_pct'])
    illustrative_equity += 1000.0 * ret / 100.0
    item = {
        'month': r['month'],
        'return_pct': ret,
        'profit': ret,
        'trades': int(float(r['trades'])),
        'wins': None,
        'losses': None,
        'be': 0,
        'pf': None,
        'win_rate': None,
        'max_dd_pct': fnum(r['max_dd_pct']),
        'avg_risk_pct': None,
        'risk_dd_0_5': 0,
        'risk_dd_5_10': 0,
        'risk_dd_10_15': 0,
        'risk_dd_gt_15': 0,
        'illustrative_equity': illustrative_equity,
    }
    monthly.append(item)
    equity.append({'month': r['month'], 'equity': illustrative_equity, 'log10_equity': math.log10(max(1.0, illustrative_equity))})
    drawdown.append({'month': r['month'], 'drawdown_pct': item['max_dd_pct']})

# Fill monthly PF/WR/risk buckets from raw+add aligned trade rows.
month_stats = {}
instr_stats = {}
risk_reason_counts = Counter()
risk_breaches = []
recompute_max_abs_diff = 0.0
for i, (raw, sized) in enumerate(zip(raw_trades, add_trades), start=1):
    if raw['symbol'] != sized['symbol'] or abs(float(raw['entry_ts']) - float(sized['entry_ts'])) > 1e-6:
        raise SystemExit(f'trade alignment mismatch at {i}: raw={raw.get("symbol")}/{raw.get("entry_ts")} sized={sized.get("symbol")}/{sized.get("entry_ts")}')
    m = sized['month']
    sym = sized['symbol']
    pnl_pct = fnum(sized['pnl_pct_of_month_start'])
    pnl_frac = pnl_pct / 100.0
    sd = fnum(raw.get('risk_pct'))
    raw_pnl = fnum(raw.get('pnl'))
    applied_pct = fnum(sized.get('applied_risk_pct'))
    recomputed = (applied_pct / 100.0) * (raw_pnl / sd) if sd > 0 else 0.0
    recompute_max_abs_diff = max(recompute_max_abs_diff, abs(recomputed - pnl_frac))
    st = month_stats.setdefault(m, {'wins': 0, 'losses': 0, 'gp': 0.0, 'gl': 0.0, 'risk_sum': 0.0, 'n': 0, 'buckets': Counter()})
    ist = instr_stats.setdefault(sym, {'trades': 0, 'wins': 0, 'losses': 0, 'gp': 0.0, 'gl': 0.0, 'ret': 0.0})
    if pnl_frac > 0:
        st['wins'] += 1; st['gp'] += pnl_frac
        ist['wins'] += 1; ist['gp'] += pnl_frac
    elif pnl_frac < 0:
        st['losses'] += 1; st['gl'] += -pnl_frac
        ist['losses'] += 1; ist['gl'] += -pnl_frac
    st['risk_sum'] += applied_pct; st['n'] += 1
    reason = sized.get('risk_reason') or 'unknown'
    st['buckets'][reason] += 1
    risk_reason_counts[reason] += 1
    if int(float(sized.get('margin_capped') or 0)):
        risk_reason_counts['margin_cap'] += 1
    ist['trades'] += 1; ist['ret'] += pnl_pct
    if pnl_pct < -3.0000001:
        risk_breaches.append({
            'loss_pct': pnl_pct,
            'idx': int(float(sized['idx'])),
            'symbol': sym,
            'month': m,
            'entry_ts': raw.get('entry_ts'),
            'side': raw.get('side'),
            'exit_type': raw.get('exit_type'),
            'avg_added': str(raw.get('avg_added')) == 'True',
            'position_size_mult': fnum(raw.get('position_size_mult'), 1.0),
            'risk_pct': sd * 100.0,
            'applied_risk_pct': applied_pct,
            'raw_pnl_pct': raw_pnl * 100.0,
            'r_multiple': raw_pnl / sd if sd > 0 else None,
            'is_reverse': str(raw.get('is_reverse')) == 'True',
        })

for item in monthly:
    st = month_stats[item['month']]
    item['wins'] = st['wins']
    item['losses'] = st['losses']
    item['pf'] = safe_pf(st['gp'], st['gl'])
    item['win_rate'] = st['wins'] / st['n'] * 100.0 if st['n'] else 0.0
    item['avg_risk_pct'] = st['risk_sum'] / st['n'] if st['n'] else 0.0
    item['risk_dd_0_5'] = st['buckets'].get('dd_0_5', 0) + st['buckets'].get('base_3pct', 0)
    item['risk_dd_5_10'] = st['buckets'].get('dd_5_10', 0)
    item['risk_dd_10_15'] = st['buckets'].get('dd_10_15', 0)
    item['risk_dd_gt_15'] = st['buckets'].get('dd_gt_15', 0)

vals = [m['return_pct'] for m in monthly]
worst_trade = min(risk_breaches, key=lambda x: x['loss_pct']) if risk_breaches else None
breach_by_exit = Counter(x['exit_type'] for x in risk_breaches)
breach_by_avg = Counter('avg_added' if x['avg_added'] else 'no_avg' for x in risk_breaches)
breach_by_reverse = Counter('reverse' if x['is_reverse'] else 'base' for x in risk_breaches)
timeout_breaches = [x for x in risk_breaches if 'timeout' in (x['exit_type'] or '')]
risk_audit = {
    'status': 'RISK_CAP_NOT_STRICT',
    'explanation': 'The 3% value is a nominal sizing cap in this artifact, not a hard maximum loss per trade. Averaging can expand position_size_mult to 2.5x, and MAX_HOLD timeout is checked before SL in the source engine.',
    'raw_trades': len(raw_trades),
    'recompute_max_abs_diff_fraction': recompute_max_abs_diff,
    'losses_below_minus_3pct': len(risk_breaches),
    'worst_loss_pct': worst_trade['loss_pct'] if worst_trade else None,
    'worst_trade': worst_trade,
    'breach_by_exit_type': dict(breach_by_exit),
    'breach_by_averaging': dict(breach_by_avg),
    'breach_by_reverse': dict(breach_by_reverse),
    'timeout_breaches': len(timeout_breaches),
    'top_10_breaches': sorted(risk_breaches, key=lambda x: x['loss_pct'])[:10],
    'recommended_fix': 'Re-run with SL-before-timeout and add-size clipped/skipped so total post-average risk to SL stays <= 3%.',
}

instruments = []
for sym, st in sorted(instr_stats.items()):
    instruments.append({
        'symbol': sym,
        'trades': st['trades'],
        'wins': st['wins'],
        'losses': st['losses'],
        'be': 0,
        'win_rate': st['wins'] / st['trades'] * 100.0 if st['trades'] else 0.0,
        'pf': safe_pf(st['gp'], st['gl']),
        'return_pct_additive': st['ret'],
    })

yearly = []
for r in add_yearly_src:
    yearly.append({
        'year': r['year'],
        'return_pct': fnum(r['return_pct']),
        'trades': int(float(r['trades'])),
        'wins': None,
        'losses': None,
        'be': 0,
        'pf': None,
        'win_rate': fnum(r['win_rate_pct']),
        'max_dd_pct': None,
    })

# Sample sized trades for curve/scatter.
sample_step = max(1, len(add_trades) // 1500)
trade_curve = []
for r in add_trades[::sample_step]:
    trade_curve.append({
        'idx': int(float(r['idx'])),
        'month': r['month'],
        'symbol': r['symbol'],
        'pnl_pct': fnum(r['pnl_pct_of_month_start']),
        'applied_risk_pct': fnum(r['applied_risk_pct']),
        'dd_after_pct': fnum(r['dd_after_pct']),
        'risk_reason': r['risk_reason'],
    })

summary = {
    'dashboard': DASH,
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'source': str(ADD_SRC),
    'raw_trade_source': str(RAW_SRC),
    'mode': 'Corrected reverse-trailing sign fix; main KPIs are monthly-reset additive 3% nominal sizing, NOT per-trade compounded income.',
    'start_equity': 1000.0,
    'final_equity': illustrative_equity,
    'final_equity_label': 'illustrative cumulative sum of monthly-reset returns; not reinvested account equity',
    'final_equity_log10': math.log10(max(1.0, illustrative_equity)),
    'final_equity_scientific': f'{illustrative_equity:.6e}',
    'return_pct': sum(vals),
    'return_pct_label': 'sum of monthly-reset additive returns; use monthly distribution as primary metric',
    'compounded_final_equity_scientific': comp_summary.get('final_equity_scientific'),
    'compounded_avg_monthly_return_pct': comp_summary.get('avg_monthly_return_pct'),
    'compounded_median_monthly_return_pct': comp_summary.get('median_monthly_return_pct'),
    'compounded_metric_warning': 'Analytical per-trade compounding only; not displayed as main monthly income metric.',
    'profit_factor': add_summary.get('profit_factor'),
    'win_rate': add_summary.get('win_rate_pct'),
    'total_trades': add_summary.get('total_trades'),
    'wins': add_summary.get('wins'),
    'losses': add_summary.get('losses'),
    'breakevens': 0,
    'total_months': len(monthly),
    'positive_months': sum(v > 0 for v in vals),
    'negative_months': sum(v < 0 for v in vals),
    'avg_monthly_return': statistics.mean(vals),
    'median_monthly_return': statistics.median(vals),
    'best_month_pct': max(vals),
    'worst_month_pct': min(vals),
    'max_drawdown_pct': add_summary.get('max_intra_month_dd_pct'),
    'worst_month_dd_pct': max(m['max_dd_pct'] for m in monthly),
    'risk_per_trade_pct': 3.0,
    'risk_cap_is_strict': False,
    'risk_audit_status': risk_audit['status'],
    'losses_below_minus_3pct': risk_audit['losses_below_minus_3pct'],
    'worst_trade_pct': risk_audit['worst_loss_pct'],
    'worst_trade': risk_audit['worst_trade'],
    'drawdown_throttle_enabled': True,
    'dd_throttle_rules': 'Monthly DD throttle in compounded artifact: 0-5%=3%, 5-10%=2%, 10-15%=1%, >15%=0.5%. Additive source shown here is flat baseline 3% with margin cap.',
    'avg_risk_per_trade_pct': add_summary.get('avg_applied_risk_pct'),
    'min_effective_risk_pct': add_summary.get('min_applied_risk_pct'),
    'max_effective_risk_pct': add_summary.get('max_applied_risk_pct'),
    'risk_reason_counts': dict(risk_reason_counts),
    'best_trade_pct': max(fnum(r['pnl_pct_of_month_start']) for r in add_trades),
    'max_win_streak': comp_summary.get('max_win_streak'),
    'max_loss_streak': comp_summary.get('max_loss_streak'),
    'avg_trades_per_month': add_summary.get('total_trades') / len(monthly),
    'old_vs_new': comparison,
}

for name, obj in [
    ('summary.json', summary),
    ('monthly.json', monthly),
    ('yearly.json', yearly),
    ('equity.json', equity),
    ('drawdown.json', drawdown),
    ('instruments.json', instruments),
    ('trade_curve_sample.json', trade_curve),
    ('risk_audit.json', risk_audit),
]:
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

html = r'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TrendFrend Risk3 DD RevTrail Fix — corrected dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{--bg:#05070b;--panel:rgba(255,255,255,.075);--panel2:rgba(255,255,255,.04);--line:rgba(255,255,255,.12);--txt:#f5f7fb;--mut:#9ca3af;--green:#30d158;--red:#ff453a;--blue:#0a84ff;--orange:#ff9f0a;--violet:#bf5af2}
*{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at 15% -5%,rgba(10,132,255,.28),transparent 32%),radial-gradient(circle at 80% 0,rgba(48,209,88,.16),transparent 30%),linear-gradient(180deg,#05070b,#0a0f19 60%,#05070b);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif}
.app{display:grid;grid-template-columns:280px 1fr;min-height:100vh} aside{position:sticky;top:0;height:100vh;padding:24px 18px;border-right:1px solid var(--line);background:rgba(5,7,11,.76);backdrop-filter:blur(20px)}
.logo{width:52px;height:52px;border-radius:16px;background:linear-gradient(145deg,#fff,#b8c2d8);color:#05070b;display:grid;place-items:center;font-weight:950;font-size:24px}.brand{display:flex;gap:13px;align-items:center;margin-bottom:25px}h1{font-size:23px;margin:0}.brand p,.mut{color:var(--mut);margin:3px 0 0;font-size:13px}.side{border:1px solid var(--line);border-radius:18px;padding:15px;margin:12px 0;background:linear-gradient(145deg,var(--panel),var(--panel2))}.side h3{margin:5px 0;color:var(--green)}.side p{color:#cbd5e1;font-size:13px;line-height:1.45}
main{padding:28px 32px 42px}.top{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:16px}h2{font-size:40px;letter-spacing:-.055em;margin:0}.badge{font-size:13px;color:var(--green);border:1px solid rgba(48,209,88,.45);border-radius:999px;padding:6px 10px;vertical-align:middle}.pill{border:1px solid var(--line);border-radius:999px;padding:10px 15px;background:rgba(255,255,255,.06);white-space:nowrap;color:#dbeafe}.notice{border:1px solid rgba(255,159,10,.52);background:rgba(255,159,10,.10);border-radius:18px;padding:13px;color:#ffd7a0;margin:12px 0 16px;line-height:1.45}.danger{border-color:rgba(255,69,58,.55);background:rgba(255,69,58,.10);color:#ffc3bd}.grid{display:grid;gap:14px}.kpis{grid-template-columns:repeat(6,1fr)}.charts{grid-template-columns:1.25fr .75fr;margin-top:14px}.two{grid-template-columns:1fr 1fr;margin-top:14px}.card{border:1px solid var(--line);border-radius:20px;background:linear-gradient(145deg,var(--panel),var(--panel2));box-shadow:0 22px 65px rgba(0,0,0,.34);padding:16px;overflow:hidden}.label{color:#c7c7cc;font-size:13px}.value{font-size:25px;font-weight:900;letter-spacing:-.04em;margin:6px 0 4px}.sub{color:var(--mut);font-size:12px;line-height:1.35}.green{color:var(--green)}.red{color:var(--red)}.orange{color:var(--orange)}.blue{color:var(--blue)}.violet{color:var(--violet)}
.section{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}.section h3{margin:0;font-size:17px}.section span{color:var(--mut);font-size:13px}.chart-card{height:330px}.chart-card canvas{height:260px!important}.mini-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}.mini{border:1px solid var(--line);border-radius:15px;padding:12px;background:rgba(0,0,0,.15)}.mini b{display:block;font-size:20px;margin:4px 0}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:var(--mut)}.table-wrap{overflow:auto;max-height:470px}.table-wrap table{min-width:980px}@media(max-width:1200px){.app{grid-template-columns:1fr}aside{display:none}.kpis,.charts,.two{grid-template-columns:1fr}.mini-grid{grid-template-columns:1fr 1fr}}
</style></head><body><div class="app"><aside>
<div class="brand"><div class="logo">TF</div><div><h1>TrendFrend</h1><p>Corrected risk audit</p></div></div>
<div class="side"><div class="label">Main KPI mode</div><h3>Monthly-reset additive</h3><p>Средний месяц теперь считается из bounded monthly-reset CSV, не из per-trade compounded curve.</p></div>
<div class="side"><div class="label">Risk audit</div><h3>3% is not strict</h3><p>Dashboard явно помечает, что текущий artifact имеет 951 сделку хуже −3% из-за averaging / timeout order.</p></div>
<div class="side"><div class="label">Fix included</div><h3>RevTrail sign fixed</h3><p>Reverse trailing after TP1 PnL sign correction remains included.</p></div>
</aside><main>
<div class="top"><div><h2>Risk3 DD Throttle <span class="badge">AUDITED</span></h2><p class="mut">Main view: corrected monthly-reset additive metrics · compounded curve is secondary analytical only.</p></div><div class="pill" id="generated">loading…</div></div>
<div class="notice">Исправлено: “средний месяц” больше не берётся из per-trade compounding. Основной KPI — monthly-reset additive. Per-trade compounded 134k% оставлен только как техническая справка.</div>
<div class="notice danger" id="riskNotice">Risk audit loading…</div>
<div class="grid kpis" id="kpis"></div>
<div class="grid charts"><div class="card chart-card"><div class="section"><h3>Illustrative additive equity</h3><span>1000 + сумма monthly-reset PnL, not reinvested</span></div><canvas id="eq"></canvas></div><div class="card chart-card"><div class="section"><h3>Monthly drawdown</h3><span id="ddSub"></span></div><canvas id="dd"></canvas></div></div>
<div class="grid two"><div class="card"><div class="section"><h3>Monthly snapshot</h3><span id="mSub"></span></div><div class="mini-grid" id="mini"></div></div><div class="card"><div class="section"><h3>Risk cap audit</h3><span>losses below −3%</span></div><canvas id="risk"></canvas></div></div>
<div class="grid two"><div class="card"><div class="section"><h3>Compounded metric quarantine</h3><span>secondary only</span></div><div class="mini-grid" id="compBox"></div></div><div class="card"><div class="section"><h3>Instrument detail</h3><span>SOL vs NEAR</span></div><table><thead><tr><th>Symbol</th><th>Trades</th><th>WR</th><th>PF</th><th>Additive return</th></tr></thead><tbody id="instRows"></tbody></table></div></div>
<div class="grid two"><div class="card"><div class="section"><h3>Monthly performance</h3><span>return · PF · WR · DD</span></div><div class="table-wrap"><table><thead><tr><th>Month</th><th>Return</th><th>PF</th><th>WR</th><th>Trades</th><th>W/L</th><th>DD</th><th>Avg risk</th></tr></thead><tbody id="monthRows"></tbody></table></div></div><div class="card"><div class="section"><h3>Worst risk breaches</h3><span>top 10</span></div><div class="table-wrap"><table><thead><tr><th>Loss</th><th>Symbol</th><th>Month</th><th>Exit</th><th>Avg</th><th>Mult</th><th>R</th></tr></thead><tbody id="breachRows"></tbody></table></div></div></div>
<div class="grid two"><div class="card"><div class="section"><h3>Yearly performance</h3><span>2021–2026</span></div><table><thead><tr><th>Year</th><th>Return</th><th>WR</th><th>Trades</th></tr></thead><tbody id="yearRows"></tbody></table></div><div class="card"><div class="section"><h3>Old vs corrected</h3><span>reverse trail sign fix</span></div><div class="mini-grid" id="delta"></div></div></div>
</main></div><script>
const BASE='/champion-live-dashboard/data/__DASH__/';
async function load(f){const r=await fetch(BASE+f+'?v='+Date.now()); if(!r.ok) throw new Error(f+' '+r.status); return r.json();}
const pct=x=>{if(x===null||x===undefined||!isFinite(x))return 'n/a'; const ax=Math.abs(x); const s=x>=0?'+':'−'; if(ax>=1e6)return s+ax.toExponential(2)+'%'; return s+ax.toLocaleString('en-US',{maximumFractionDigits:2})+'%';};
const num=x=>Number(x||0).toLocaleString('en-US',{maximumFractionDigits:2}); const pf=x=>x?Number(x).toFixed(2):'∞'; const cls=x=>x>=0?'green':'red';
Promise.all([load('summary.json'),load('monthly.json'),load('yearly.json'),load('equity.json'),load('drawdown.json'),load('instruments.json'),load('risk_audit.json')]).then(([s,m,y,e,d,ins,ra])=>{
 document.getElementById('generated').textContent='Generated: '+new Date(s.generated_at).toLocaleString();
 document.getElementById('riskNotice').innerHTML=`<b>Risk status: ${ra.status}</b><br>${ra.explanation}<br>Losses below −3%: <b>${ra.losses_below_minus_3pct}</b>; worst: <b>${pct(ra.worst_loss_pct)}</b>. Recommended: ${ra.recommended_fix}`;
 const kpis=[['Avg month',pct(s.avg_monthly_return),'green','monthly-reset additive'],['Median month',pct(s.median_monthly_return),'green','primary income KPI'],['Worst month',pct(s.worst_month_pct),'red','monthly reset'],['Best month',pct(s.best_month_pct),'green','monthly reset'],['PF',pf(s.profit_factor),'green','from sized trades'],['Win rate',num(s.win_rate)+'%','green',s.wins+' / '+s.losses],['Trades',s.total_trades.toLocaleString(),'','corrected source'],['Max DD',pct(-s.max_drawdown_pct),'red','intra-month'],['Worst trade',pct(s.worst_trade_pct),'red','risk cap breach'],['>3% losses',s.losses_below_minus_3pct.toLocaleString(),'orange','not strict risk cap'],['Avg risk',num(s.avg_risk_per_trade_pct)+'%','orange','after margin cap'],['Comp avg month',pct(s.compounded_avg_monthly_return_pct),'violet','quarantined analytical']];
 document.getElementById('kpis').innerHTML=kpis.map(a=>`<div class="card"><div class="label">${a[0]}</div><div class="value ${a[2]}">${a[1]}</div><div class="sub">${a[3]}</div></div>`).join('');
 const best=m.reduce((a,b)=>a.return_pct>b.return_pct?a:b), worst=m.reduce((a,b)=>a.return_pct<b.return_pct?a:b), ddworst=m.reduce((a,b)=>a.max_dd_pct>b.max_dd_pct?a:b);
 document.getElementById('ddSub').textContent='Max −'+num(s.max_drawdown_pct)+'%'; document.getElementById('mSub').textContent=s.positive_months+'/'+s.total_months+' profitable months';
 const minis=[['Avg month',pct(s.avg_monthly_return),'green'],['Median',pct(s.median_monthly_return),'green'],['Best',pct(best.return_pct),'green',best.month],['Worst',pct(worst.return_pct),cls(worst.return_pct),worst.month],['Worst DD',pct(-ddworst.max_dd_pct),'red',ddworst.month],['Positive',s.positive_months+' / '+s.total_months,'green'],['Sum monthly',pct(s.return_pct),'green'],['Final illustrative',num(s.final_equity),'blue']];
 document.getElementById('mini').innerHTML=minis.map(a=>`<div class="mini"><span class="label">${a[0]}</span><b class="${a[2]||''}">${a[1]}</b><span class="sub">${a[3]||''}</span></div>`).join('');
 const comp=[['Comp avg',pct(s.compounded_avg_monthly_return_pct),'violet'],['Comp median',pct(s.compounded_median_monthly_return_pct),'violet'],['Comp final',s.compounded_final_equity_scientific,'violet'],['Warning','not main KPI','orange']];
 document.getElementById('compBox').innerHTML=comp.map(a=>`<div class="mini"><span class="label">${a[0]}</span><b class="${a[2]}">${a[1]}</b></div>`).join('');
 const old=s.old_vs_new||{}, oldDD=old.old_dd_compound||{}, newDD=old.new_dd_compound||{};
 const deltas=[['WR',num(oldDD.win_rate_pct)+' → '+num(newDD.win_rate_pct)+'%','green'],['PF',pf(oldDD.profit_factor_fractional)+' → '+pf(newDD.profit_factor_fractional),'green'],['Max DD',num(oldDD.max_global_drawdown_pct)+' → '+num(newDD.max_global_drawdown_pct)+'%','green'],['Changed PnL',(old.changed_raw_trades?.changed_pnl||0).toLocaleString(),'orange']];
 document.getElementById('delta').innerHTML=deltas.map(a=>`<div class="mini"><span class="label">${a[0]}</span><b class="${a[2]}">${a[1]}</b></div>`).join('');
 document.getElementById('monthRows').innerHTML=m.map(r=>`<tr><td><b>${r.month}</b></td><td class="${cls(r.return_pct)}">${pct(r.return_pct)}</td><td>${pf(r.pf)}</td><td>${num(r.win_rate)}%</td><td>${r.trades}</td><td>${r.wins} / ${r.losses}</td><td class="red">${pct(-r.max_dd_pct)}</td><td>${num(r.avg_risk_pct)}%</td></tr>`).join('');
 document.getElementById('yearRows').innerHTML=y.map(r=>`<tr><td><b>${r.year}</b></td><td class="${cls(r.return_pct)}">${pct(r.return_pct)}</td><td>${num(r.win_rate)}%</td><td>${r.trades}</td></tr>`).join('');
 document.getElementById('instRows').innerHTML=ins.map(r=>`<tr><td><b>${r.symbol}</b></td><td>${r.trades}</td><td>${num(r.win_rate)}%</td><td>${pf(r.pf)}</td><td class="${cls(r.return_pct_additive)}">${pct(r.return_pct_additive)}</td></tr>`).join('');
 document.getElementById('breachRows').innerHTML=ra.top_10_breaches.map(r=>`<tr><td class="red">${pct(r.loss_pct)}</td><td>${r.symbol}</td><td>${r.month}</td><td>${r.exit_type}</td><td>${r.avg_added?'yes':'no'}</td><td>${num(r.position_size_mult)}</td><td>${num(r.r_multiple)}</td></tr>`).join('');
 const grid={color:'rgba(255,255,255,.08)'}, tick={color:'#9ca3af'};
 new Chart(document.getElementById('eq'),{type:'line',data:{labels:e.map(x=>x.month),datasets:[{data:e.map(x=>x.equity),borderColor:'#30d158',backgroundColor:'rgba(48,209,88,.18)',fill:true,borderWidth:2,tension:.22,pointRadius:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:tick},y:{grid:grid,ticks:tick}}}});
 new Chart(document.getElementById('dd'),{type:'line',data:{labels:d.map(x=>x.month),datasets:[{data:d.map(x=>-x.drawdown_pct),borderColor:'#ff453a',backgroundColor:'rgba(255,69,58,.17)',fill:true,borderWidth:2,tension:.22,pointRadius:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:tick},y:{max:0,grid:grid,ticks:tick}}}});
 const be=ra.breach_by_exit_type||{}; new Chart(document.getElementById('risk'),{type:'doughnut',data:{labels:Object.keys(be),datasets:[{data:Object.values(be),backgroundColor:['#ff453a','#ff9f0a','#bf5af2','#0a84ff'],borderWidth:0}]},options:{plugins:{legend:{position:'right',labels:{color:'#c7c7cc'}}},cutout:'58%'}});
}).catch(e=>{document.body.innerHTML='<pre style="color:white;padding:30px">Dashboard load error: '+e.stack+'</pre>'; console.error(e);});
</script></body></html>'''.replace('__DASH__', DASH)

(OUT / 'index.html').write_text(html, encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
print('RISK_AUDIT', json.dumps(risk_audit, ensure_ascii=False, indent=2))
print('WROTE', OUT / 'index.html')
print('DATA', DATA)
