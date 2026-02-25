"""
generate_dashboard.py — Builds dashboard.html from project output files.
Run: python generate_dashboard.py  →  opens dashboard.html
"""
import pandas as pd
import json
import os
import webbrowser

# ── Load data ────────────────────────────────────────────────────────────────
df = pd.read_csv("optimization_actions_report.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp")

# KPI values from summary report
def parse_summary():
    kpis = {"snapshots": "—", "acc_gain": "—", "annual_savings": "—", "sim_savings": "—", "model_mae": "—", "naive_mae": "—"}
    try:
        with open("milestone_4_summary_report.txt", encoding="utf-8") as f:
            for line in f:
                if "Snapshots" in line:         kpis["snapshots"]      = line.split(":")[1].strip()
                if "Accuracy Gain" in line:     kpis["acc_gain"]       = line.split(":")[1].strip()
                if "Annual Savings" in line:    kpis["annual_savings"] = line.split("$")[1].strip() if "$" in line else "—"
                if "Simulation Savings" in line:kpis["sim_savings"]    = line.split("$")[1].strip() if "$" in line else "—"
                if "Model MAE" in line:         kpis["model_mae"]      = line.split(":")[1].strip()
                if "Naive Baseline" in line:    kpis["naive_mae"]      = line.split(":")[1].strip()
    except FileNotFoundError:
        pass
    return kpis

kpis = parse_summary()

# Action breakdown
actions = df["infrastructure_action"].value_counts().to_dict()
upscale   = actions.get("UPSCALE", 0)
downscale = actions.get("DOWNSCALE", 0)
maintain  = actions.get("MAINTAIN", 0)

# Chart data: group by region
regions = df["region"].unique().tolist()
region_data = {}
for r in regions:
    sub = df[df["region"] == r].sort_values("timestamp")
    region_data[r] = {
        "timestamps": sub["timestamp"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
        "actual":     [round(v, 2) for v in sub["usage_units"].tolist()],
        "forecast":   [round(v, 2) for v in sub["forecasted_usage"].tolist()],
        "capacity":   [round(v, 2) for v in sub["recommended_capacity"].tolist()],
    }

# Table data (last 20 rows)
table_rows = df.tail(20)[["timestamp","region","service_type","usage_units",
                           "forecasted_usage","recommended_capacity","infrastructure_action"]].copy()
table_rows["timestamp"] = table_rows["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
table_json = table_rows.to_dict("records")

# ── HTML ─────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Azure Demand Forecasting Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet"/>
  <style>
    :root {{
      --bg:        #0f1117;
      --surface:   #1a1d27;
      --card:      #21263a;
      --border:    #2e3450;
      --accent:    #4f8ef7;
      --green:     #34d399;
      --red:       #f87171;
      --amber:     #fbbf24;
      --text:      #e2e8f0;
      --muted:     #8892a4;
      --font:      'Inter', sans-serif;
      --radius:    12px;
      --gap:       24px;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font);
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 32px var(--gap);
    }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}

    /* ── Header ── */
    header {{
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 32px; flex-wrap: wrap; gap: 16px;
    }}
    header h1 {{ font-size: 1.6rem; font-weight: 700; letter-spacing: -0.5px; }}
    header h1 span {{ color: var(--accent); }}
    .badge {{
      background: var(--card); border: 1px solid var(--border);
      border-radius: 999px; padding: 6px 16px; font-size: 0.8rem; color: var(--muted);
    }}

    /* ── KPI grid ── */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: var(--gap); margin-bottom: var(--gap);
    }}
    .kpi {{
      background: var(--card); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 20px 24px;
      position: relative; overflow: hidden;
      transition: transform .2s, box-shadow .2s;
    }}
    .kpi:hover {{ transform: translateY(-4px); box-shadow: 0 8px 32px rgba(0,0,0,.4); }}
    .kpi::before {{
      content: ''; position: absolute; inset: 0 0 auto 0;
      height: 3px; background: var(--accent-color, var(--accent));
    }}
    .kpi-label {{ font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; margin-bottom: 8px; }}
    .kpi-value {{ font-size: 1.55rem; font-weight: 700; color: var(--value-color, var(--text)); }}
    .kpi-sub   {{ font-size: 0.75rem; color: var(--muted); margin-top: 4px; }}

    /* ── Two-col layout ── */
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: var(--gap); margin-bottom: var(--gap); }}
    @media(max-width: 900px) {{ .row {{ grid-template-columns: 1fr; }} }}

    /* ── Cards ── */
    .card {{
      background: var(--card); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 24px;
    }}
    .card h2 {{ font-size: 0.9rem; font-weight: 600; color: var(--muted); margin-bottom: 18px; text-transform: uppercase; letter-spacing: .06em; }}
    .card canvas {{ width: 100% !important; }}

    /* ── Region tabs ── */
    .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }}
    .tab-btn {{
      padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border);
      background: transparent; color: var(--muted); cursor: pointer; font-size: 0.8rem;
      font-family: var(--font); transition: all .15s;
    }}
    .tab-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
    .tab-btn.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}

    /* ── Action donut labels ── */
    .action-legend {{ display: flex; gap: 16px; justify-content: center; margin-top: 12px; flex-wrap: wrap; }}
    .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 0.8rem; }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}

    /* ── Table ── */
    .table-wrap {{ overflow-x: auto; margin-bottom: var(--gap); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
    th {{
      background: var(--surface); color: var(--muted); text-align: left;
      padding: 10px 14px; font-weight: 600; text-transform: uppercase;
      font-size: 0.7rem; letter-spacing: .05em; border-bottom: 1px solid var(--border);
      position: sticky; top: 0;
    }}
    td {{ padding: 10px 14px; border-bottom: 1px solid var(--border); color: var(--text); }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: rgba(79,142,247,.05); }}
    .chip {{
      display: inline-block; padding: 2px 10px; border-radius: 999px;
      font-size: 0.72rem; font-weight: 600; letter-spacing: .04em;
    }}
    .chip-upscale   {{ background: rgba(248,113,113,.15); color: var(--red); }}
    .chip-downscale {{ background: rgba(52,211,153,.15);  color: var(--green); }}
    .chip-maintain  {{ background: rgba(251,191,36,.15);  color: var(--amber); }}

    footer {{ text-align: center; color: var(--muted); font-size: 0.75rem; margin-top: 40px; }}
  </style>
</head>
<body>

<header>
  <h1>☁ Azure <span>Demand Forecasting</span> Dashboard</h1>
  <span class="badge">Capacity Optimization System · 2026</span>
</header>

<!-- KPIs -->
<div class="kpi-grid">
  <div class="kpi" style="--accent-color:#4f8ef7">
    <div class="kpi-label">Snapshots Analyzed</div>
    <div class="kpi-value">{kpis["snapshots"]}</div>
    <div class="kpi-sub">Latest 500 rows evaluated</div>
  </div>
  <div class="kpi" style="--accent-color:#34d399;--value-color:#34d399">
    <div class="kpi-label">Model MAE</div>
    <div class="kpi-value">{kpis["model_mae"]}</div>
    <div class="kpi-sub">Naive baseline: {kpis["naive_mae"]}</div>
  </div>
  <div class="kpi" style="--accent-color:#a78bfa;--value-color:#a78bfa">
    <div class="kpi-label">Accuracy Gain vs Naive</div>
    <div class="kpi-value">{kpis["acc_gain"]}</div>
    <div class="kpi-sub">Over last-value baseline</div>
  </div>
  <div class="kpi" style="--accent-color:#34d399;--value-color:#34d399">
    <div class="kpi-label">Annual Savings Impact</div>
    <div class="kpi-value">${kpis["annual_savings"]}</div>
    <div class="kpi-sub">$120M per 1% accuracy gain</div>
  </div>
  <div class="kpi" style="--accent-color:#fbbf24;--value-color:#fbbf24">
    <div class="kpi-label">Simulation Savings</div>
    <div class="kpi-value">${kpis["sim_savings"]}</div>
    <div class="kpi-sub">Waste reduction estimate</div>
  </div>
  <div class="kpi" style="--accent-color:#f87171">
    <div class="kpi-label">UPSCALE Actions</div>
    <div class="kpi-value" style="color:var(--red)">{upscale}</div>
    <div class="kpi-sub">Nodes needing more capacity</div>
  </div>
  <div class="kpi" style="--accent-color:#34d399">
    <div class="kpi-label">DOWNSCALE Actions</div>
    <div class="kpi-value" style="color:var(--green)">{downscale}</div>
    <div class="kpi-sub">Over-provisioned nodes</div>
  </div>
  <div class="kpi" style="--accent-color:#fbbf24">
    <div class="kpi-label">MAINTAIN Actions</div>
    <div class="kpi-value" style="color:var(--amber)">{maintain}</div>
    <div class="kpi-sub">Within optimal threshold</div>
  </div>
</div>

<!-- Charts row 1 -->
<div class="row">
  <div class="card" style="grid-column: 1 / -1;">
    <h2>Actual vs Forecast — by Region</h2>
    <div class="tabs" id="regionTabs"></div>
    <canvas id="lineChart" height="100"></canvas>
  </div>
</div>

<!-- Charts row 2 -->
<div class="row">
  <div class="card">
    <h2>Infrastructure Action Breakdown</h2>
    <canvas id="donutChart" height="200"></canvas>
    <div class="action-legend">
      <div class="legend-item"><div class="legend-dot" style="background:#f87171"></div>UPSCALE ({upscale})</div>
      <div class="legend-item"><div class="legend-dot" style="background:#34d399"></div>DOWNSCALE ({downscale})</div>
      <div class="legend-item"><div class="legend-dot" style="background:#fbbf24"></div>MAINTAIN ({maintain})</div>
    </div>
  </div>
  <div class="card">
    <h2>Recommended vs Provisioned Capacity</h2>
    <canvas id="barChart" height="200"></canvas>
  </div>
</div>

<!-- Table -->
<div class="card table-wrap">
  <h2>Latest 20 Provisioning Actions</h2>
  <table id="actionTable">
    <thead>
      <tr>
        <th>Timestamp</th><th>Region</th><th>Service</th>
        <th>Actual Usage</th><th>Forecast</th><th>Rec. Capacity</th><th>Action</th>
      </tr>
    </thead>
    <tbody id="tableBody"></tbody>
  </table>
</div>

<footer>Azure Demand Forecasting &amp; Capacity Optimization System · Auto-generated dashboard</footer>

<script>
const REGION_DATA = {json.dumps(region_data)};
const TABLE_DATA  = {json.dumps(table_json)};

// ── Colour palette ──────────────────────────────────────────────────────────
const PALETTE = ['#4f8ef7','#34d399','#f87171','#a78bfa','#fbbf24','#38bdf8','#fb923c'];

// ── Region tabs + line chart ────────────────────────────────────────────────
const regions = Object.keys(REGION_DATA);
let lineChart = null;
let currentRegion = regions[0];

function buildTabs() {{
  const tabsEl = document.getElementById('regionTabs');
  regions.forEach((r, i) => {{
    const btn = document.createElement('button');
    btn.className = 'tab-btn' + (i === 0 ? ' active' : '');
    btn.textContent = r.toUpperCase();
    btn.onclick = () => {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentRegion = r;
      updateLineChart(r);
    }};
    tabsEl.appendChild(btn);
  }});
}}

function buildLineChart(region) {{
  const d = REGION_DATA[region];
  const ctx = document.getElementById('lineChart').getContext('2d');
  lineChart = new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: d.timestamps,
      datasets: [
        {{ label: 'Actual Usage',          data: d.actual,   borderColor: '#4f8ef7', backgroundColor: 'rgba(79,142,247,.08)', tension: 0.3, pointRadius: 0, borderWidth: 2, fill: true }},
        {{ label: 'Forecasted Usage',      data: d.forecast, borderColor: '#34d399', backgroundColor: 'transparent',          tension: 0.3, pointRadius: 0, borderWidth: 2, borderDash: [5,4] }},
        {{ label: 'Recommended Capacity',  data: d.capacity, borderColor: '#fbbf24', backgroundColor: 'transparent',          tension: 0.3, pointRadius: 0, borderWidth: 1.5, borderDash: [2,3] }},
      ]
    }},
    options: {{
      responsive: true,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{ legend: {{ labels: {{ color: '#8892a4', font: {{ size: 11 }} }} }} }},
      scales: {{
        x: {{ ticks: {{ color: '#8892a4', maxTicksLimit: 8 }}, grid: {{ color: '#2e3450' }} }},
        y: {{ ticks: {{ color: '#8892a4' }}, grid: {{ color: '#2e3450' }} }}
      }}
    }}
  }});
}}

function updateLineChart(region) {{
  const d = REGION_DATA[region];
  lineChart.data.labels = d.timestamps;
  lineChart.data.datasets[0].data = d.actual;
  lineChart.data.datasets[1].data = d.forecast;
  lineChart.data.datasets[2].data = d.capacity;
  lineChart.update('active');
}}

// ── Donut chart ─────────────────────────────────────────────────────────────
function buildDonut() {{
  new Chart(document.getElementById('donutChart').getContext('2d'), {{
    type: 'doughnut',
    data: {{
      labels: ['UPSCALE', 'DOWNSCALE', 'MAINTAIN'],
      datasets: [{{ data: [{upscale}, {downscale}, {maintain}], backgroundColor: ['#f87171','#34d399','#fbbf24'], borderWidth: 0, hoverOffset: 8 }}]
    }},
    options: {{
      cutout: '68%',
      plugins: {{ legend: {{ display: false }} }},
    }}
  }});
}}

// ── Bar chart: capacity comparison per region ────────────────────────────────
function buildBar() {{
  const labels = [], rec = [], prov = [];
  TABLE_DATA.forEach(r => {{
    if (!labels.includes(r.region)) {{
      labels.push(r.region);
      rec.push(r.recommended_capacity);
      prov.push(r.provisioned_capacity_allocated);
    }}
  }});
  new Chart(document.getElementById('barChart').getContext('2d'), {{
    type: 'bar',
    data: {{
      labels,
      datasets: [
        {{ label: 'Recommended', data: rec,  backgroundColor: 'rgba(79,142,247,.7)', borderRadius: 4 }},
        {{ label: 'Provisioned', data: prov, backgroundColor: 'rgba(248,113,113,.7)', borderRadius: 4 }}
      ]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ labels: {{ color: '#8892a4', font: {{ size: 11 }} }} }} }},
      scales: {{
        x: {{ ticks: {{ color: '#8892a4' }}, grid: {{ color: '#2e3450' }} }},
        y: {{ ticks: {{ color: '#8892a4' }}, grid: {{ color: '#2e3450' }} }}
      }}
    }}
  }});
}}

// ── Table ────────────────────────────────────────────────────────────────────
function buildTable() {{
  const tbody = document.getElementById('tableBody');
  TABLE_DATA.forEach(r => {{
    const chipClass = r.infrastructure_action === 'UPSCALE'   ? 'chip-upscale'
                    : r.infrastructure_action === 'DOWNSCALE' ? 'chip-downscale'
                    : 'chip-maintain';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${{r.timestamp}}</td>
      <td>${{r.region}}</td>
      <td>${{r.service_type}}</td>
      <td>${{r.usage_units?.toFixed(1)}}</td>
      <td>${{r.forecasted_usage?.toFixed(1)}}</td>
      <td>${{r.recommended_capacity?.toFixed(1)}}</td>
      <td><span class="chip ${{chipClass}}">${{r.infrastructure_action}}</span></td>
    `;
    tbody.appendChild(tr);
  }});
}}

// ── Init ─────────────────────────────────────────────────────────────────────
buildTabs();
buildLineChart(currentRegion);
buildDonut();
buildBar();
buildTable();
</script>
</body>
</html>"""

out_path = "dashboard.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Dashboard saved → {out_path}")
webbrowser.open(os.path.abspath(out_path))
