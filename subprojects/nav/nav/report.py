"""A self-contained HTML report."""

import json
from typing import List

import pandas as pd

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NAV</title>
<style>
  :root { color-scheme: light dark; --fg: #1a1a1a; --muted: #6b6b6b; --bg: #fafafa; --line: #e0e0e0; }
  @media (prefers-color-scheme: dark) {
    :root { --fg: #e8e8e8; --muted: #9a9a9a; --bg: #16181d; --line: #2c2f36; }
  }
  body { margin: 0; padding: 24px; background: var(--bg); color: var(--fg);
         font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif; }
  .wrap { max-width: 900px; margin: 0 auto; }
  h1 { font-size: 15px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
       color: var(--muted); margin: 0 0 4px; }
  .nav { font-size: 34px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .sub { color: var(--muted); font-variant-numeric: tabular-nums; }
  .up { color: #1a7f37; } .down { color: #c0392b; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px;
           background: #f5c26b33; color: #8a6100; }
  @media (prefers-color-scheme: dark) { .badge { color: #f0c674; } }
  .toggle { margin: 20px 0 8px; }
  button { font: inherit; padding: 5px 14px; border: 1px solid var(--line);
           background: transparent; color: var(--fg); cursor: pointer; }
  button[aria-pressed="true"] { background: var(--fg); color: var(--bg); }
  button:first-of-type { border-radius: 6px 0 0 6px; }
  button:last-of-type { border-radius: 0 6px 6px 0; border-left: 0; }
  table { border-collapse: collapse; width: 100%; margin-top: 28px; }
  th, td { padding: 7px 10px; border-bottom: 1px solid var(--line); text-align: right;
           font-variant-numeric: tabular-nums; }
  th:first-child, td:first-child { text-align: left; font-variant-numeric: normal; }
  th { color: var(--muted); font-weight: 500; font-size: 12px; text-transform: uppercase;
       letter-spacing: .04em; }
  .cash td:first-child { color: var(--muted); }
  canvas { margin-top: 8px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Net asset value</h1>
  <div class="nav" id="nav"></div>
  <div class="sub" id="sub"></div>
  <div class="sub" id="stale"></div>

  <div class="toggle">
    <button id="btn-krw" aria-pressed="true">KRW</button
    ><button id="btn-usd" aria-pressed="false">USD</button>
  </div>
  <canvas id="chart" height="110"></canvas>

  <table>
    <thead><tr><th>Ticker</th><th>Quantity</th><th>Price (KRW)</th>
    <th>Value (KRW)</th><th>Weight</th></tr></thead>
    <tbody id="holdings"></tbody>
  </table>
</div>

<script type="application/json" id="nav-data">__PAYLOAD__</script>
<script src="__CHARTJS__"></script>
<script>
const data = JSON.parse(document.getElementById("nav-data").textContent);
const fmt = (v, d) => v.toLocaleString(undefined, {minimumFractionDigits: d, maximumFractionDigits: d});
const s = data.summary;

document.getElementById("nav").textContent = fmt(s.nav_krw, 0) + " KRW";
const dir = s.change_krw > 0 ? "up" : (s.change_krw < 0 ? "down" : "");
const arrow = s.change_krw > 0 ? "\\u25b2" : (s.change_krw < 0 ? "\\u25bc" : "=");
document.getElementById("sub").innerHTML =
  fmt(s.nav_usd, 2) + " USD &middot; <span class='" + dir + "'>" + arrow + " " +
  fmt(Math.abs(s.change_krw), 0) + " KRW (" + (s.change_pct * 100).toFixed(2) + "%)</span>" +
  " &middot; " + s.date + " &middot; USDKRW " + fmt(s.fx_usdkrw, 2);
if (s.stale.length) {
  document.getElementById("stale").innerHTML =
    "<span class='badge'>carried forward: " + s.stale.join(", ") + "</span>";
}

const body = document.getElementById("holdings");
data.holdings.forEach(h => {
  const tr = document.createElement("tr");
  if (h.is_cash) tr.className = "cash";
  [h.ticker, fmt(h.quantity, 4).replace(/\\.?0+$/, ""), fmt(h.price_krw, 2),
   fmt(h.value_krw, 0), (h.weight * 100).toFixed(1) + "%"].forEach(v => {
    const td = document.createElement("td");
    td.textContent = v;
    tr.appendChild(td);
  });
  body.appendChild(tr);
});

const labels = data.series.map(r => r.date);
const chart = new Chart(document.getElementById("chart"), {
  type: "line",
  data: {labels, datasets: [{
    data: data.series.map(r => r.nav_krw),
    borderColor: "#4c78a8", borderWidth: 2, pointRadius: 0, tension: 0.15, fill: false
  }]},
  options: {
    responsive: true, maintainAspectRatio: true,
    plugins: {legend: {display: false}},
    scales: {x: {ticks: {maxTicksLimit: 8}}, y: {ticks: {callback: v => fmt(v, 0)}}}
  }
});

function setCurrency(currency) {
  const krw = currency === "krw";
  chart.data.datasets[0].data = data.series.map(r => krw ? r.nav_krw : r.nav_usd);
  chart.update();
  document.getElementById("btn-krw").setAttribute("aria-pressed", krw);
  document.getElementById("btn-usd").setAttribute("aria-pressed", !krw);
}
document.getElementById("btn-krw").onclick = () => setCurrency("krw");
document.getElementById("btn-usd").onclick = () => setCurrency("usd");
</script>
</body>
</html>
"""


def build_payload(frame: pd.DataFrame, holdings: List[dict], summary: dict) -> dict:
    series = [
        {
            "date": str(pd.Timestamp(row["date"]).date()),
            "nav_krw": float(row["nav_krw"]),
            "nav_usd": float(row["nav_usd"]),
        }
        for row in frame.to_dict("records")
    ]
    return {
        "series": series,
        "holdings": holdings,
        "summary": {
            "date": str(pd.Timestamp(summary["date"]).date()),
            "nav_krw": float(summary["nav_krw"]),
            "nav_usd": float(summary["nav_usd"]),
            "change_krw": float(summary["change_krw"]),
            "change_pct": float(summary["change_pct"]),
            "fx_usdkrw": float(summary["fx_usdkrw"]),
            "stale": summary["stale"],
        },
    }


def render_html(payload: dict) -> str:
    # json.dumps does not escape "<", so a raw "<" inside any string in the
    # payload (a ticker or stale entry from user-edited symbols.yaml) can
    # corrupt the page even without a literal "</" substring: "<!--" followed
    # by "<script" drives the HTML tokenizer into the "script data double
    # escaped" state, in which the *legitimate* closing "</script>" of the
    # nav-data block only demotes the state instead of closing the element,
    # swallowing the Chart.js tag and the app script as inert text with no
    # visible error. Escaping every "<" as its JSON unicode escape forecloses
    # "</script", "<script" and "<!--" all at once, and round-trips through
    # JSON.parse unchanged since < is a valid JSON escape for "<".
    serialized = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    # Substitute __CHARTJS__ first and __PAYLOAD__ last: __CHARTJS__ never
    # appears inside `serialized`, but the reverse order would let a payload
    # string that happens to spell "__CHARTJS__" get rewritten into the CDN
    # URL by the second .replace(), scanning text that already came from the
    # (attacker- or just unluckily-named) payload -- the same root cause as
    # the "<" hazard above, corrupting the JSON the same way.
    return TEMPLATE.replace("__CHARTJS__", CHART_JS).replace("__PAYLOAD__", serialized)
