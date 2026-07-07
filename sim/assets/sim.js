/* Claude Code 投資シミュレーター — マーケットデスク */
"use strict";

const $ = (s) => document.querySelector(s);
const yen = (x, d = 0) =>
  x == null ? "–" : "¥" + x.toLocaleString("ja-JP", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (x) => (x == null ? "–" : `${x > 0 ? "+" : ""}${x.toFixed(2)}%`);
const dcls = (x) => (x == null || Math.abs(x) < 0.005 ? "delta-flat" : x > 0 ? "delta-up" : "delta-down");

const PALETTE = ["#3987e5", "#199e70", "#c98500", "#9085e9", "#e87ba4", "#2eb82e", "#e66767", "#6d7681"];

async function j(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}
function escapeHtml(s) {
  return (s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function sparkPath(values, w = 100, h = 22) {
  const v = values.filter((x) => x != null);
  if (v.length < 2) return "";
  const min = Math.min(...v), max = Math.max(...v), span = max - min || 1;
  return v.map((x, i) =>
    `${(i / (v.length - 1) * w).toFixed(1)},${(h - 1 - (x - min) / span * (h - 2)).toFixed(1)}`
  ).join(" ");
}

const state = { market: null, portfolio: null, trades: null, focusKey: null, candleCache: new Map() };

/* ---- ティッカーテープ ---- */
function renderTape(mk) {
  const items = mk.instruments.map((i) => {
    const cls = dcls(i.chg1d);
    return `<span class="t-item"><b>${i.name_ja}</b> ${yen(i.close, i.close < 10 ? 4 : 2)} ` +
      `<span class="${cls}">${pct(i.chg1d)}</span></span>`;
  }).join("");
  $("#tape").innerHTML = items + items; // 2周ぶん複製してループを継ぎ目なく
}

/* ---- 統計行 ---- */
function renderStats(pf) {
  const equity = pf.history.length ? pf.history[pf.history.length - 1].equity : pf.cash;
  const totalPnl = equity - pf.invested;
  const totalPct = pf.invested ? (totalPnl / pf.invested) * 100 : 0;

  $("#st-equity").textContent = yen(equity);
  $("#st-equity-sub").textContent = `現金 ${yen(pf.cash)} + ポジション ${yen(equity - pf.cash)}`;

  $("#st-total-pnl").textContent = (totalPnl >= 0 ? "+" : "") + yen(totalPnl);
  $("#st-total-pnl").className = "value " + dcls(totalPnl);
  $("#st-total-pnl-sub").textContent = `${pct(totalPct)} ・ 元本 ${yen(pf.invested)}`;

  $("#st-open-pnl").textContent = (pf.open_pnl >= 0 ? "+" : "") + yen(pf.open_pnl);
  $("#st-open-pnl").className = "value " + dcls(pf.open_pnl);
  $("#st-open-pnl-sub").textContent = `保有 ${pf.positions.length} 銘柄`;

  $("#st-realized").textContent = (pf.realized_pnl >= 0 ? "+" : "") + yen(pf.realized_pnl);
  $("#st-realized").className = "value " + dcls(pf.realized_pnl);
  $("#st-realized-sub").textContent = `約定 ${state.trades.trades.length} 件・ 勝率集計は判断ログ参照`;
}

/* ---- ウォッチリスト ---- */
function renderWatchlist(mk) {
  $("#watchlist").innerHTML = mk.instruments.map((i) => `
    <div class="w-row ${i.key === state.focusKey ? "on" : ""}" data-key="${i.key}" data-symbol="${i.symbol}" role="button" tabindex="0">
      <div>
        <div class="w-name">${i.name_ja}</div>
        <div class="w-code">${i.symbol}</div>
      </div>
      <div class="w-price">${yen(i.close, i.close < 10 ? 4 : 2)}</div>
      <div class="w-chg ${dcls(i.chg1d)}">${pct(i.chg1d)}</div>
      <svg viewBox="0 0 100 22" preserveAspectRatio="none"><polyline points="${sparkPath(i.spark)}" fill="none" stroke="${i.chg1d >= 0 ? "#2eb82e" : "#e66767"}" stroke-width="1.5"/></svg>
    </div>`).join("");
  document.querySelectorAll(".w-row").forEach((el) => {
    const go = () => focusSymbol(el.dataset.key, el.dataset.symbol);
    el.addEventListener("click", go);
    el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
  });
}

/* ---- フォーカスチャート(ローソク足) ---- */
let focusChart = null, focusCandle = null;

function initFocusChart() {
  focusChart = LightweightCharts.createChart($("#chart-focus"), {
    autoSize: true,
    layout: {
      background: { type: "solid", color: "transparent" },
      textColor: "#6d7681", fontSize: 11, attributionLogo: false,
      fontFamily: '"IBM Plex Mono", Consolas, monospace',
    },
    grid: { vertLines: { color: "#1f242c" }, horzLines: { color: "#1f242c" } },
    rightPriceScale: { borderColor: "#1f242c" },
    timeScale: { borderColor: "#1f242c" },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    localization: { locale: "ja-JP" },
  });
  focusCandle = focusChart.addCandlestickSeries({
    upColor: "#0ca30c", downColor: "#d03b3b", borderVisible: false,
    wickUpColor: "#0ca30c", wickDownColor: "#d03b3b",
  });
}

async function loadCandles(key) {
  if (!state.candleCache.has(key)) {
    try {
      state.candleCache.set(key, await j(`data/candles/${key}.json`));
    } catch {
      state.candleCache.set(key, { bars: [] });
    }
  }
  return state.candleCache.get(key);
}

async function focusSymbol(key, symbol) {
  state.focusKey = key;
  renderWatchlist(state.market);
  const inst = state.market.instruments.find((i) => i.symbol === symbol);
  const d = await loadCandles(key);
  const bars = (d.bars || []).filter((b) => b[4] != null);
  focusCandle.setData(bars.map((b) => ({ time: b[0], open: b[1], high: b[2], low: b[3], close: b[4] })));
  focusChart.timeScale().fitContent();

  $("#f-name").textContent = inst ? `${inst.name_ja} (${inst.symbol})` : symbol;
  $("#f-price").textContent = yen(inst?.close, inst?.close < 10 ? 4 : 2);
  const chgEl = $("#f-chg");
  chgEl.textContent = pct(inst?.chg1d);
  chgEl.className = "f-chg " + dcls(inst?.chg1d);
  $("#f-date").textContent = inst?.close_date ?? "";
}

/* ---- 資産推移 ---- */
function renderEquityChart(pf) {
  const chart = LightweightCharts.createChart($("#chart-equity"), {
    autoSize: true,
    layout: {
      background: { type: "solid", color: "transparent" },
      textColor: "#6d7681", fontSize: 11, attributionLogo: false,
      fontFamily: '"IBM Plex Mono", Consolas, monospace',
    },
    grid: { vertLines: { color: "#1f242c" }, horzLines: { color: "#1f242c" } },
    rightPriceScale: { borderColor: "#1f242c" },
    timeScale: { borderColor: "#1f242c" },
    localization: { locale: "ja-JP", priceFormatter: (v) => "¥" + Math.round(v).toLocaleString("ja-JP") },
  });
  const eq = chart.addLineSeries({ color: "#3987e5", lineWidth: 2, priceLineVisible: false });
  const inv = chart.addLineSeries({
    color: "#6d7681", lineWidth: 2, priceLineVisible: false, lastValueVisible: false,
    lineStyle: LightweightCharts.LineStyle.Dotted,
  });
  eq.setData(pf.history.map((h) => ({ time: h.date, value: h.equity })));
  inv.setData(pf.history.map((h) => ({ time: h.date, value: h.invested })));
  chart.timeScale().fitContent();
  $("#eq-note").textContent = `全スナップショットの時価評価`;
}

/* ---- 資産配分ドーナツ ---- */
function donutSVG(slices, cx, cy, r, thickness) {
  const total = slices.reduce((s, x) => s + x.value, 0) || 1;
  let angle = -Math.PI / 2;
  const arcs = slices.map((s) => {
    const frac = s.value / total;
    const a0 = angle, a1 = angle + frac * 2 * Math.PI;
    angle = a1;
    const large = frac > 0.5 ? 1 : 0;
    const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0);
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
    if (frac >= 0.9999) {
      return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${s.color}" stroke-width="${thickness}"/>`;
    }
    return `<path d="M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}" fill="none" stroke="${s.color}" stroke-width="${thickness}"/>`;
  }).join("");
  return `<svg class="donut" viewBox="0 0 150 150">${arcs}
    <text x="75" y="72" text-anchor="middle" class="donut-center">${yen(total)}</text>
    <text x="75" y="86" text-anchor="middle" class="donut-center-label">TOTAL EQUITY</text>
  </svg>`;
}

function renderAllocation(pf) {
  const equity = pf.history.length ? pf.history[pf.history.length - 1].equity : pf.cash;
  const rows = pf.positions.map((p, i) => ({
    label: p.name_ja, value: p.value, color: PALETTE[i % PALETTE.length],
  }));
  rows.push({ label: "現金", value: pf.cash, color: "#3a3f47" });

  $("#alloc").innerHTML =
    donutSVG(rows, 75, 75, 58, 26) +
    `<table class="alloc-table">
      <tbody>${rows.map((r) => `
        <tr>
          <td><span class="dot" style="background:${r.color}"></span>${r.label}</td>
          <td class="num">${yen(r.value)}</td>
          <td class="num">${equity ? (r.value / equity * 100).toFixed(1) : "0.0"}%</td>
        </tr>`).join("")}
      </tbody>
    </table>`;
}

/* ---- 保有ポジション ---- */
function renderPositions(pf) {
  if (!pf.positions.length) {
    $("#positions-body").innerHTML =
      `<tr><td colspan="7" class="empty">保有ポジションはまだありません(現金 ${yen(pf.cash)})</td></tr>`;
    return;
  }
  $("#positions-body").innerHTML = pf.positions.map((p) => `
    <tr>
      <td>${p.name_ja}<br><span style="color:var(--muted);font-size:10.5px;font-family:var(--mono)">${p.symbol}</span></td>
      <td class="num">${p.qty}</td>
      <td class="num">${yen(p.avg_cost, p.avg_cost < 10 ? 2 : 0)}</td>
      <td class="num">${yen(p.close, p.close < 10 ? 2 : 0)}</td>
      <td class="num">${yen(p.value)}</td>
      <td class="num ${dcls(p.pnl)}">${p.pnl == null ? "–" : (p.pnl >= 0 ? "+" : "") + yen(p.pnl)}</td>
      <td class="num ${dcls(p.pnl_pct)}">${pct(p.pnl_pct)}</td>
    </tr>`).join("");
}

/* ---- 売買履歴 ---- */
function renderTrades(tr) {
  if (!tr.trades.length) {
    $("#trades-body").innerHTML = `<tr><td colspan="7" class="empty">取引はまだありません</td></tr>`;
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

/* ---- AI判断 ---- */
function renderJournal(dc) {
  const latest = dc.decisions[0];
  if (!latest) { $("#j-summary").textContent = "まだ判断の記録がありません"; return; }
  $("#j-date").textContent = `${latest.date}`;
  $("#j-summary").textContent = latest.summary;
  $("#j-detail").textContent = latest.detail;
}
function renderDecisions(dc) {
  const past = dc.decisions.slice(1);
  if (!past.length) {
    $("#decisions").innerHTML = `<p style="color:var(--muted);font-size:12.5px">過去の判断はまだありません。</p>`;
    return;
  }
  $("#decisions").innerHTML = past.map((d) => `
    <div class="decision">
      <div class="head" role="button" tabindex="0">
        <span class="date">${d.date}</span>
        <span class="summary">${escapeHtml(d.summary)}</span>
        <span class="toggle-hint">クリックで全文</span>
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
    .map((i) => `${i.name_ja}(${i.symbol.replace(".T", "")}${i.min_lot !== 1 ? `・最小${i.min_lot}` : ""})`)
    .join("、 ");
}

async function init() {
  try {
    const [meta, pf, tr, dc, mk] = await Promise.all([
      j("data/meta.json"), j("data/portfolio.json"), j("data/trades.json"),
      j("data/decisions.json"), j("data/market.json"),
    ]);
    state.market = mk; state.portfolio = pf; state.trades = tr;

    const dt = new Date(meta.exported_at).toLocaleString("ja-JP", { dateStyle: "medium", timeStyle: "short" });
    $("#meta-line").textContent = `最終更新: ${dt} / 価格データ最新日: ${meta.latest_price_date ?? "未取得"}`;

    const badge = $("#live-badge");
    if (!meta.latest_price_date) {
      badge.textContent = "NO DATA"; badge.classList.add("stale");
      $("#banner").innerHTML = `<div class="banner">市場価格データはまだ未取得です。GitHub Actions の初回実行後に価格・売買が始まります。</div>`;
    } else {
      badge.textContent = `LIVE ・ ${meta.latest_price_date}`;
    }

    renderTape(mk);
    renderStats(pf);
    renderWatchlist(mk);
    initFocusChart();
    // 保有ポジション優先、なければ株式・ETFの先頭を初期フォーカスにする
    const heldSymbols = new Set(pf.positions.map((p) => p.symbol));
    const initial =
      mk.instruments.find((i) => heldSymbols.has(i.symbol)) ??
      mk.instruments.find((i) => i.kind !== "crypto") ??
      mk.instruments[0];
    if (initial) await focusSymbol(initial.key, initial.symbol);
    renderEquityChart(pf);
    renderAllocation(pf);
    renderPositions(pf);
    renderJournal(dc);
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
