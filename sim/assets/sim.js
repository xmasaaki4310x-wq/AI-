/* Claude Code 投資シミュレーターUI */
"use strict";

const $ = (s) => document.querySelector(s);
const yen = (x, d = 0) =>
  x == null ? "–" : "¥" + x.toLocaleString("ja-JP", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (x) => (x == null ? "–" : `${x > 0 ? "+" : ""}${x.toFixed(2)}%`);
const dcls = (x) => (x == null || Math.abs(x) < 0.005 ? "flat" : x > 0 ? "up" : "down");

async function j(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

function renderSummary(pf) {
  const equity = pf.history.length ? pf.history[pf.history.length - 1].equity : pf.cash;
  const pnl = equity - pf.invested;
  const pnlPct = pf.invested ? (pnl / pf.invested) * 100 : 0;
  const posValue = equity - pf.cash;
  $("#summary-tiles").innerHTML = `
    <div class="tile"><span class="label">資産総額</span>
      <span class="value">${yen(equity)}</span>
      <span class="sub">現金 ${yen(pf.cash)} + ポジション ${yen(posValue)}</span></div>
    <div class="tile"><span class="label">累計入金(元本)</span>
      <span class="value">${yen(pf.invested)}</span>
      <span class="sub">毎月¥10,000積立</span></div>
    <div class="tile"><span class="label">評価損益</span>
      <span class="value delta ${dcls(pnl)}">${pnl >= 0 ? "+" : ""}${yen(pnl)}</span>
      <span class="sub delta ${dcls(pnl)}">${pct(pnlPct)}</span></div>
    <div class="tile"><span class="label">記録日数 / 取引回数</span>
      <span class="value">${pf.history.length}日</span>
      <span class="sub" id="trade-count">–</span></div>`;
}

function renderEquityChart(pf) {
  const chart = LightweightCharts.createChart($("#chart-equity"), {
    autoSize: true,
    layout: {
      background: { type: "solid", color: "transparent" },
      textColor: "#8a8f98", fontSize: 11, attributionLogo: false,
    },
    grid: { vertLines: { color: "#262a31" }, horzLines: { color: "#262a31" } },
    rightPriceScale: { borderColor: "#262a31" },
    timeScale: { borderColor: "#262a31" },
    localization: {
      locale: "ja-JP",
      priceFormatter: (v) => "¥" + Math.round(v).toLocaleString("ja-JP"),
    },
  });
  const eq = chart.addLineSeries({ color: "#3987e5", lineWidth: 2, priceLineVisible: false });
  const inv = chart.addLineSeries({ color: "#8a8f98", lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
  eq.setData(pf.history.map((h) => ({ time: h.date, value: h.equity })));
  inv.setData(pf.history.map((h) => ({ time: h.date, value: h.invested })));
  chart.timeScale().fitContent();
}

function renderPositions(pf) {
  if (!pf.positions.length) {
    $("#positions-body").innerHTML =
      `<tr><td colspan="6" style="text-align:center;color:var(--muted)">保有ポジションはまだありません(現金 ${yen(pf.cash)})</td></tr>`;
    return;
  }
  $("#positions-body").innerHTML = pf.positions.map((p) => `
    <tr>
      <td>${p.name_ja}<br><span style="color:var(--muted);font-size:11px">${p.symbol}</span></td>
      <td class="num">${p.qty}</td>
      <td class="num">${yen(p.avg_cost, p.avg_cost < 10 ? 2 : 0)}</td>
      <td class="num">${yen(p.close, p.close < 10 ? 2 : 0)}<br><span style="color:var(--muted);font-size:11px">${p.close_date ?? ""}</span></td>
      <td class="num">${yen(p.value)}</td>
      <td class="num delta ${dcls(p.pnl_pct)}">${pct(p.pnl_pct)}</td>
    </tr>`).join("");
}

function renderTrades(tr) {
  $("#trade-count").textContent = `${tr.trades.length}回`;
  if (!tr.trades.length) {
    $("#trades-body").innerHTML =
      `<tr><td colspan="7" style="text-align:center;color:var(--muted)">取引はまだありません</td></tr>`;
    return;
  }
  $("#trades-body").innerHTML = tr.trades.map((t) => `
    <tr>
      <td class="num">${t.date}</td>
      <td><span class="side-badge ${t.side.toLowerCase()}">${t.side === "BUY" ? "買" : "売"}</span></td>
      <td>${t.symbol}</td>
      <td class="num">${t.qty}</td>
      <td class="num">${yen(t.price, t.price < 10 ? 2 : 0)}</td>
      <td class="num">${yen(t.fee, 0)}</td>
      <td class="reason">${escapeHtml(t.reason)}</td>
    </tr>`).join("");
}

function renderDecisions(dc) {
  $("#decisions").innerHTML = dc.decisions.map((d) => `
    <div class="decision">
      <div class="head" role="button" tabindex="0">
        <span class="date">${d.date}</span>
        <span class="summary">${escapeHtml(d.summary)}</span>
        <span class="toggle-hint">クリックで詳細</span>
      </div>
      <div class="detail">${escapeHtml(d.detail)}</div>
    </div>`).join("");
  document.querySelectorAll(".decision .head").forEach((el) => {
    const toggle = () => el.parentElement.classList.toggle("open");
    el.addEventListener("click", toggle);
    el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
  });
}

function renderUniverse(mk) {
  $("#universe-list").textContent = mk.instruments
    .map((i) => `${i.name_ja}(${i.symbol.replace(".T", "")}${i.min_lot > 1 || i.min_lot < 1 ? `・最小${i.min_lot}` : ""})`)
    .join("、 ");
}

function escapeHtml(s) {
  return (s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function init() {
  try {
    const [meta, pf, tr, dc, mk] = await Promise.all([
      j("data/meta.json"), j("data/portfolio.json"), j("data/trades.json"),
      j("data/decisions.json"), j("data/market.json"),
    ]);
    const dt = new Date(meta.exported_at).toLocaleString("ja-JP", { dateStyle: "medium", timeStyle: "short" });
    $("#meta-line").textContent =
      `最終更新: ${dt} / 価格データ最新日: ${meta.latest_price_date ?? "未取得"}`;
    if (!meta.latest_price_date) {
      $("#banner").innerHTML =
        `<div class="banner">⏳ 市場価格データはまだ未取得です。GitHub Actions の初回実行後に価格・売買が始まります。</div>`;
    }
    renderSummary(pf);
    renderEquityChart(pf);
    renderPositions(pf);
    renderTrades(tr);
    renderDecisions(dc);
    renderUniverse(mk);
  } catch (e) {
    $("#banner").innerHTML =
      `<div class="banner">データの読み込みに失敗しました(${e.message})。ローカルではHTTPサーバー経由で開いてください。</div>`;
    console.error(e);
  }
}

document.addEventListener("DOMContentLoaded", init);
