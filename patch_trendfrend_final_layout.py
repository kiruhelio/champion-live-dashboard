from pathlib import Path

p = Path("trendfrend/index.html")
s = p.read_text()

START = "<!-- TRENDFREND_FINAL_LAYOUT_PATCH_START -->"
END = "<!-- TRENDFREND_FINAL_LAYOUT_PATCH_END -->"

while START in s and END in s:
    a = s.index(START)
    b = s.index(END) + len(END)
    s = s[:a] + s[b:]

patch = r'''
<!-- TRENDFREND_FINAL_LAYOUT_PATCH_START -->
<style>
.tf-pies-vertical{
  display:grid;
  grid-template-columns:1fr;
  gap:16px;
}
.tf-pie-box{
  border:1px solid rgba(255,255,255,.10);
  border-radius:14px;
  padding:12px;
  background:rgba(0,0,0,.15);
}
.tf-pie-box canvas{
  height:210px!important;
}
.tf-wide-table{
  overflow:auto;
}
.tf-wide-table table{
  min-width:1050px;
}
</style>

<script>
setTimeout(async function(){
  const BASE='/champion-live-dashboard/data/baseline_v2026_07/';
  const fmt=(v,d=2)=>Number(v||0).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
  const plus=v=>Number(v)>=0?'+':'';
  const cls=v=>Number(v)>=0?'green':'red';

  async function load(f){
    const r=await fetch(BASE+f+'?v='+Date.now(),{cache:'no-store'});
    if(!r.ok) throw new Error(f+' '+r.status);
    return await r.json();
  }

  const [isum, icontrib] = await Promise.all([
    load('instrument_summary.json'),
    load('instrument_monthly_contribution.json')
  ]);

  const sol = isum.find(x=>x.symbol==='SOL') || {};
  const near = isum.find(x=>x.symbol==='NEAR') || {};

  const instCard = [...document.querySelectorAll('.card')].find(card=>{
    const h = card.querySelector('h3');
    return h && h.textContent.trim() === 'Инструменты';
  });

  if(instCard){
    instCard.innerHTML = `
      <div class="section">
        <h3>Инструменты</h3>
        <span>структура сделок / результат</span>
      </div>

      <div class="tf-pies-vertical">
        <div class="tf-pie-box">
          <div class="label">Соотношение сделок</div>
          <canvas id="tradePieVertical"></canvas>
        </div>

        <div class="tf-pie-box">
          <div class="label">Прибыльные / убыточные сделки</div>
          <canvas id="wlPieVertical"></canvas>
        </div>
      </div>

      <table style="margin-top:14px">
        <thead>
          <tr>
            <th>Инструмент</th>
            <th>Вклад</th>
            <th>Доля</th>
            <th>Сделок</th>
            <th>Win / Loss</th>
          </tr>
        </thead>
        <tbody>
          ${[sol,near].map(x=>`
            <tr>
              <td><b>${x.symbol}</b></td>
              <td class="${cls(x.contribution_pct)}">${plus(x.contribution_pct)}${fmt(x.contribution_pct)}%</td>
              <td><b>${fmt(x.share_of_return_pct)}%</b></td>
              <td><b>${fmt(x.trades,0)}</b></td>
              <td><span class="green">${fmt(x.wins,0)}</span> / <span class="red">${fmt(x.losses,0)}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;

    new Chart(document.getElementById('tradePieVertical'),{
      type:'doughnut',
      data:{
        labels:['SOL','NEAR'],
        datasets:[{
          data:[sol.trades||0, near.trades||0],
          backgroundColor:['#30d158','#0a84ff'],
          borderWidth:0
        }]
      },
      options:{
        plugins:{legend:{position:'right',labels:{color:'#c7c7cc'}}},
        cutout:'58%'
      }
    });

    new Chart(document.getElementById('wlPieVertical'),{
      type:'doughnut',
      data:{
        labels:['Прибыльные','Убыточные'],
        datasets:[{
          data:[(sol.wins||0)+(near.wins||0), (sol.losses||0)+(near.losses||0)],
          backgroundColor:['#30d158','#ff453a'],
          borderWidth:0
        }]
      },
      options:{
        plugins:{legend:{position:'right',labels:{color:'#c7c7cc'}}},
        cutout:'58%'
      }
    });
  }

  const monthlyCard = [...document.querySelectorAll('.card')].find(card=>{
    const h = card.querySelector('h3');
    return h && h.textContent.trim().includes('Помесячная доходность');
  });

  if(monthlyCard){
    const oldContrib = monthlyCard.querySelector('#contribTable');
    if(oldContrib){
      const oldTable = oldContrib.closest('table');
      const oldSection = oldTable ? oldTable.previousElementSibling : null;
      if(oldTable) oldTable.remove();
      if(oldSection && oldSection.classList.contains('section')) oldSection.remove();
    }

    if(!document.getElementById('monthlyInstrumentContribution')){
      const names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      const by = {};

      icontrib.forEach(r=>{
        const y = r.month.slice(0,4);
        const mi = Number(r.month.slice(5,7)) - 1;
        by[y] ??= {
          SOL: Array(12).fill(null),
          NEAR: Array(12).fill(null),
          total: Array(12).fill(null),
          sumSOL: 0,
          sumNEAR: 0,
          sumTotal: 0
        };

        const solVal = Number(r.symbols?.SOL?.contribution_pct || 0);
        const nearVal = Number(r.symbols?.NEAR?.contribution_pct || 0);
        const totalVal = Number(r.total_return_pct || 0);

        by[y].SOL[mi] = solVal;
        by[y].NEAR[mi] = nearVal;
        by[y].total[mi] = totalVal;
        by[y].sumSOL += solVal;
        by[y].sumNEAR += nearVal;
        by[y].sumTotal += totalVal;
      });

      const block = document.createElement('div');
      block.id = 'monthlyInstrumentContribution';
      block.innerHTML = `
        <div style="margin-top:18px" class="section">
          <h3>Ежемесячный вклад инструментов в доходность (%)</h3>
          <span>SOL / NEAR по месяцам</span>
        </div>

        <div class="tf-wide-table">
          <table>
            <thead>
              <tr>
                <th>Год</th>
                <th>Инструмент</th>
                ${names.map(m=>`<th>${m}</th>`).join('')}
                <th>Итого</th>
              </tr>
            </thead>
            <tbody>
              ${Object.keys(by).sort().map(y=>{
                const row = by[y];

                const makeRow = (sym, arr, sum, firstCol) => `
                  <tr>
                    <td><b>${firstCol ? y : ''}</b></td>
                    <td><b>${sym}</b></td>
                    ${arr.map(v=>v===null ? '<td>—</td>' : `<td class="${cls(v)}">${plus(v)}${fmt(v,1)}%</td>`).join('')}
                    <td class="${cls(sum)}"><b>${plus(sum)}${fmt(sum,1)}%</b></td>
                  </tr>
                `;

                return makeRow('SOL', row.SOL, row.sumSOL, true) +
                       makeRow('NEAR', row.NEAR, row.sumNEAR, false) +
                       `<tr style="opacity:.75">
                          <td></td>
                          <td><b>Итого</b></td>
                          ${row.total.map(v=>v===null ? '<td>—</td>' : `<td class="${cls(v)}">${plus(v)}${fmt(v,1)}%</td>`).join('')}
                          <td class="${cls(row.sumTotal)}"><b>${plus(row.sumTotal)}${fmt(row.sumTotal,1)}%</b></td>
                        </tr>`;
              }).join('')}
            </tbody>
          </table>
        </div>
      `;
      monthlyCard.appendChild(block);
    }
  }
}, 900);
</script>
<!-- TRENDFREND_FINAL_LAYOUT_PATCH_END -->
'''

s = s.replace("</body>", patch + "\n</body>")
p.write_text(s)
print("TrendFrend layout patched")
