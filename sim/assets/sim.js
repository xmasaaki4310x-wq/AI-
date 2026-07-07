/* Claude Code 投資シミュレーター — 運用実験日誌UI */
"use strict";

const $ = (s) => document.querySelector(s);
const yen = (x, d = 0) =>
  x == null ? "–" : "¥" + x.toLocaleString("ja-JP", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (x) => (x == null ? "–" : `${x > 0 ? "+" : ""}${x.toFixed(2)}%`);
const dcls = (x) => (x == null || Math.abs(x) < 0.005 ? "delta-flat" : x > 0 ? "delta-up" : "delta-down");

async function j(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

function escapeHtml(s) {
  return (s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---- ヒーロー(通帳の最新行) ---- */
function renderHero(pf, tr, meta) {
  const equity = pf.history.length ? pf.history[pf.history.length - 1].equity : pf.cash;
  const pnl = equity - pf.invested;
  const pnlPct = pf.invested ? (pnl / pf.invested) * 100 : 0;
  const posValue = equity - pf.cash;

  $("#hero-equity").textContent = yen(equity);
  $("#hero-ledger").innerHTML = `
    <div class="ledger-row"><span class="lbl">累計入金(元本)</span><span class="leader"></span><span class="val">${yen(pf.invested)}</span></div>
    <div class="ledger-row"><span class="lbl">評価損益</span><span class="leader"></span><span class="val ${dcls(pnl)}">${pnl >= 0 ? "+" : ""}${yen(pnl)} (${pct(pnlPct)})</span></div>
    <div class="ledger-row"><span class="lbl">内訳</span><span class="leader"></span><span class="val">現金 ${yen(pf.cash)} / 保有 ${yen(posValue)}</span></div>`;

  const start = pf.deposits.length ? pf.deposits[0].date : "–";
  $("#hero-meta").textContent =
    `実験開始 ${start} ・ 記録 ${pf.history.length}日 ・ 取引 ${tr.trades.length}回 ・ 毎月¥10,000積立`;

  const d = meta.latest_price_date;
  $("#stamp-date").textContent = d ? d.slice(5).replace("-", "/") : "–";
}

/* ---- 本日の判断(日誌) ---- */
function renderJournal(dc) {
  const latest = dc.decisions[0];
  if (!latest) {
    $("#j-summary").textContent = "まだ判断の記録がありません";
    return;
  }
  $("#j-date").textContent = `${latest.date} 記`;
  $("#j-summary").textContent = latest.summary;
  $("#j-detail").textContent = latest.detail;
}

/* ---- 資産推移 ---- */
function renderEquityChart(pf) {
  const chart = LightweightCharts.createChart($("#chart-equity"), {
    autoSize: true,
    layout: {
      background: { type: "solid", color: "transparent" },
      textColor: "#7d8a82", fontSize: 11, attributionLogo: false,
      fontFamily: '"IBM Plex Mono", Consolas, monospace',
    },
    grid: {
      vertLines: { color: "rgba(43,90,122,0.10)" },
      horzLines: { color: "rgba(43,90,122,0.10)" },
    },
    rightPriceScale: { borderColor: "rgba(43,90,122,0.35)" },
    timeScale: { borderColor: "rgba(43,90,122,0.35)" },
    localization: {
      locale: "ja-JP",
      priceFormatter: (v) => "¥" + Math.round(v).toLocaleString("ja-JP"),
    },
  });
  const eq = chart.addLineSeries({ color: "#2b5a7a", lineWidth: 2, priceLineVisible: false });
  const inv = chart.addLineSeries({
    color: "#9aa8a0", lineWidth: 2, priceLineVisible: false, lastValueVisible: false,
    lineStyle: LightweightCharts.LineStyle.Dotted,
  });
  eq.setData(pf.history.map((h) => ({ time: h.date, value: h.equity })));
  inv.setData(pf.history.map((h) => ({ time: h.date, value: h.invested })));
  chart.timeScale().fitContent();
}

/* ---- 保有ポジション ---- */
function renderPositions(pf) {
  if (!pf.positions.length) {
    $("#positions-body").innerHTML =
      `<tr><td colspan="6" class="empty">保有ポジションはまだありません(現金 ${yen(pf.cash)})</td></tr>`;
    return;
  }
  $("#positions-body").innerHTML = pf.positions.map((p) => `
    <tr>
      <td>${p.name_ja}<br><span style="color:var(--muted);font-size:11px;font-family:var(--mono)">${p.symbol}</span></td>
      <td class="num">${p.qty}</td>
      <td class="num">${yen(p.avg_cost, p.avg_cost < 10 ? 2 : 0)}</td>
      <td class="num">${yen(p.close, p.close < 10 ? 2 : 0)}<br><span style="color:var(--muted);font-size:11px">${p.close_date ?? ""}</span></td>
      <td class="num">${yen(p.value)}</td>
      <td class="num ${dcls(p.pnl_pct)}">${pct(p.pnl_pct)}</td>
    </tr>`).join("");
}

/* ---- 売買履歴 ---- */
function renderTrades(tr) {
  if (!tr.trades.length) {
    $("#trades-body").innerHTML =
      `<tr><td colspan="7" class="empty">取引はまだありません</td></tr>`;
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

/* ---- 過去の判断 ---- */
function renderDecisions(dc) {
  const past = dc.decisions.slice(1);
  if (!past.length) {
    $("#decisions").innerHTML = `<p class="section-desc">過去の判断はまだありません。</p>`;
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
    const dt = new Date(meta.exported_at).toLocaleString("ja-JP", { dateStyle: "medium", timeStyle: "short" });
    $("#meta-line").textContent =
      `最終記帳: ${dt} / 価格データ最新日: ${meta.latest_price_date ?? "未取得"}`;
    if (!meta.latest_price_date) {
      $("#banner").innerHTML =
        `<div class="banner">市場価格データはまだ未取得です。GitHub Actions の初回実行後に価格・売買が始まります。</div>`;
    }
    renderHero(pf, tr, meta);
    renderJournal(dc);
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
