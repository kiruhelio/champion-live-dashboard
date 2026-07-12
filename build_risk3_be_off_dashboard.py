#!/usr/bin/env python3
import json, html, math
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DASH = 'risk3-be-off-current-20260712'
SRC = Path('/home/ubuntu/.hermes/bots/research_near_only_baseline_20260709_181451/out_bybit_taker_be_off_current_settings_20260712')
OUT = ROOT / DASH
DATA = ROOT / 'data' / DASH
OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)
summary = json.loads((SRC / 'summary.json').read_text(encoding='utf-8'))
summary['dashboard'] = DASH
summary['generated_at'] = datetime.now(timezone.utc).isoformat()
summary['source'] = str(SRC)
summary['live_bot_status'] = {
    'be_after_tp1_disabled_in_live_config': True,
    'live_config': '/home/ubuntu/.hermes/bots/champion_bybit_demo_bot/config_candidate.json',
    'live_code': '/home/ubuntu/.hermes/bots/champion_bybit_demo_bot/live_champion_bot.py',
    'service': 'champion-bybit-demo-bot',
}
(DATA / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

def fmt(x, d=2):
    if x is None: return '—'
    try:
        x=float(x)
    except Exception:
        return html.escape(str(x))
    if abs(x) >= 1e9:
        return f'{x:.3e}'
    return f'{x:,.{d}f}'

def pct(x,d=2): return fmt(x,d)+'%'
res = {r['label']: r for r in summary['results']}
on = res['be_after_tp1_ON_current_config']
off = res['be_after_tp1_OFF_requested']
params = summary['parameters']
metrics = [
    ('Win rate', 'win_rate_pct', 'pp'),
    ('Profit factor', 'profit_factor', 'num'),
    ('Avg month additive', 'avg_month_additive_pct', 'pct'),
    ('Median month additive', 'median_month_additive_pct', 'pct'),
    ('Worst month additive', 'worst_month_additive_pct', 'pct'),
    ('Max monthly DD', 'max_monthly_dd_pct', 'pct'),
    ('Profitable months', 'profitable_months_compound', 'cnt'),
]
rows=''
for name,key,kind in metrics:
    a=on.get(key); b=off.get(key); delta=(b-a) if isinstance(a,(int,float)) and isinstance(b,(int,float)) else None
    val_on = pct(a) if kind in ('pct','pp') else fmt(a,3) if kind=='num' else str(a)
    val_off = pct(b) if kind in ('pct','pp') else fmt(b,3) if kind=='num' else str(b)
    val_delta = (('+' if delta and delta>0 else '') + (pct(delta) if kind in ('pct','pp') else fmt(delta,3))) if delta is not None else '—'
    cls='pos' if delta is not None and ((key!='max_monthly_dd_pct' and delta>0) or (key=='max_monthly_dd_pct' and delta<0)) else 'neg' if delta is not None and delta!=0 else ''
    rows += f'<tr><td>{name}</td><td>{val_on}</td><td><b>{val_off}</b></td><td class="{cls}">{val_delta}</td></tr>'

cards = f'''
<div class="card"><div class="label">BE after TP1</div><div class="big bad">OFF</div><div>live config + code patched</div></div>
<div class="card"><div class="label">PF / WR</div><div class="big">{fmt(off['profit_factor'],3)} / {pct(off['win_rate_pct'])}</div><div>40,386 trades</div></div>
<div class="card"><div class="label">Avg / Median month</div><div class="big">{pct(off['avg_month_additive_pct'])} / {pct(off['median_month_additive_pct'])}</div><div>monthly-reset additive</div></div>
<div class="card"><div class="label">Worst month / DD</div><div class="big warn">{pct(off['worst_month_additive_pct'])} / {pct(off['max_monthly_dd_pct'])}</div><div>still aggressive risk profile</div></div>
'''

def small_table(items, cols):
    out='<table><thead><tr>'+''.join(f'<th>{c}</th>' for c in cols)+'</tr></thead><tbody>'
    for it in items:
        out+='<tr>'+''.join(f'<td>{html.escape(str(it.get(c,"")))}</td>' for c in cols)+'</tr>'
    return out+'</tbody></table>'

sym_rows=''
for s in off['symbol_breakdown']:
    sym_rows += f"<tr><td>{s['symbol']}</td><td>{s['trades']}</td><td>{pct(s['win_rate_pct'])}</td><td>{fmt(s['profit_factor'],3)}</td><td>{pct(s['pnl_pct_sum'])}</td></tr>"
exit_rows=''
for k,v in sorted(off['exit_type_counts'].items(), key=lambda x:-x[1]):
    exit_rows += f'<tr><td>{html.escape(k)}</td><td>{v}</td></tr>'
worst_rows=''
for m in off['worst_months_by_compound'][:10]:
    worst_rows += f"<tr><td>{m['month']}</td><td>{pct(m['additive_return_pct'])}</td><td>{pct(m['compound_return_pct'])}</td><td>{m['trades']}</td><td>{pct(m['max_dd_pct'])}</td></tr>"

chart_labels=json.dumps([m['month'] for m in off['worst_months_by_compound'][:10]], ensure_ascii=False)
chart_vals=json.dumps([m['additive_return_pct'] for m in off['worst_months_by_compound'][:10]])
html_text=f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TrendFrend Risk3 BE OFF — 20260712</title>
<style>
body{{margin:0;background:#08111f;color:#e7eefc;font:15px Inter,system-ui,Segoe UI,Arial}} .wrap{{max-width:1180px;margin:auto;padding:28px}}
h1{{font-size:34px;margin:0 0 8px}} .sub{{color:#9fb1d1;margin-bottom:22px}} .grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}} .card{{background:#101d33;border:1px solid #22375c;border-radius:18px;padding:18px;box-shadow:0 8px 30px #0005}} .label{{color:#98aac8;font-size:13px}} .big{{font-size:26px;font-weight:800;margin:8px 0}} .bad{{color:#ff6b7a}} .warn{{color:#ffd166}} .pos{{color:#4ade80}} .neg{{color:#fb7185}}
section{{background:#0d1a2e;border:1px solid #22375c;border-radius:18px;padding:18px;margin-top:18px}} table{{width:100%;border-collapse:collapse}} th,td{{border-bottom:1px solid #22375c;padding:9px;text-align:left}} th{{color:#9fb1d1}} code{{background:#06101e;padding:2px 5px;border-radius:6px}} a{{color:#7dd3fc}} .note{{color:#b8c6df;line-height:1.45}} @media(max-width:900px){{.grid{{grid-template-columns:1fr 1fr}}}} @media(max-width:560px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">
<h1>TrendFrend / Risk 3% / BE after TP1 OFF</h1>
<div class="sub">SOL/NEAR, 3m+1h, ATR filter 0.0, TP1_R 1.0, TP2_R 4.5, averaging ON, Bybit taker fee 0.055%/side. Generated {summary['generated_at']}</div>
<div class="grid">{cards}</div>
<section><h2>ON vs OFF сравнение</h2><table><thead><tr><th>Metric</th><th>BE ON</th><th>BE OFF</th><th>Delta OFF-ON</th></tr></thead><tbody>{rows}</tbody></table></section>
<section><h2>Вывод</h2><div class="note">BE OFF исторически чуть лучше по PF, среднему месяцу, худшему месяцу и максимальной просадке, но уменьшает win rate: часть сделок после TP1 теперь может вернуться к исходному SL вместо закрытия по BE. Профиль остаётся агрессивным: max monthly DD около <b>{pct(off['max_monthly_dd_pct'])}</b>, worst month additive <b>{pct(off['worst_month_additive_pct'])}</b>.</div></section>
<section><h2>Инструменты</h2><table><thead><tr><th>Symbol</th><th>Trades</th><th>WR</th><th>PF</th><th>PnL sum</th></tr></thead><tbody>{sym_rows}</tbody></table></section>
<section><h2>Exit types — BE OFF</h2><table><thead><tr><th>Exit</th><th>Count</th></tr></thead><tbody>{exit_rows}</tbody></table></section>
<section><h2>Worst months — BE OFF</h2><table><thead><tr><th>Month</th><th>Additive</th><th>Compound</th><th>Trades</th><th>Max DD</th></tr></thead><tbody>{worst_rows}</tbody></table></section>
<section><h2>Files</h2><div class="note">Data JSON: <code>data/{DASH}/summary.json</code><br>Research source: <code>{html.escape(str(SRC))}</code><br>Live config: <code>/home/ubuntu/.hermes/bots/champion_bybit_demo_bot/config_candidate.json</code></div></section>
</div></body></html>'''
(OUT/'index.html').write_text(html_text, encoding='utf-8')
(ROOT/'index.html').write_text('''<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=risk3-be-off-current-20260712/"><a href="risk3-be-off-current-20260712/">risk3-be-off-current-20260712</a>''', encoding='utf-8')
print(OUT)
print(DATA/'summary.json')
