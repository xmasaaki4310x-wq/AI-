/* 世界株式マーケット・ダッシュボード
 * チャート描画: TradingView lightweight-charts (Apache-2.0) を同梱使用
 * データ: pipeline/ (yfinance + stockstats + backtesting.py + quantstats) が生成したJSON
 */
"use strict";

const COLORS = {
  up: "#0ca30c", down: "#d03b3b",
  upA: "rgba(12,163,12,0.55)", downA: "rgba(208,59,59,0.55)",
  s1: "#3987e5", s2: "#199e70", s3: "#c98500", s4: "#9085e9",
  baseline: "#8a8f98", grid: "#262a31", muted: "#8a8f98",
  bb: "rgba(138,143,152,0.7)",
};
const STRAT_COLORS = { sma_cross: COLORS.s1, rsi_revert: COLORS.s2, bb_breakout: COLORS.s3 };
const MARKETS = ["すべて", "米国", "日本", "欧州", "アジア", "FX", "暗号資産", "商品"];

const state = {
  meta: null, screener: null, backtests: null,
  market: "すべて", symbol: null,
  symCache: new Map(),
  sort: { key: null, dir: -1 },
  charts: {}, series: {}, timeIndex: new Map(),
};

/* ---------- ユーティリティ ---------- */
const $ = (sel) => document.querySelector(sel);

function fmtPrice(x, ref) {
  if (x == null) return "–";
  const d = (ref ?? x) < 10 ? 4 : 2;
  return x.toLocaleString("ja-JP", { minimumFractionDigits: d, maximumFractionDigits: d });
}
function fmtPct(x, signed = true) {
  if (x == null) return "–";
  const s = signed && x > 0 ? "+" : "";
  return `${s}${x.toFixed(2)}%`;
}
function fmtCompact(x) {
  if (x == null || x === 0) return "–";
  return new Intl.NumberFormat("ja-JP", { notation: "compact", maximumFractionDigits: 1 }).format(x);
}
function deltaClass(x) { return x == null || Math.abs(x) < 0.005 ? "flat" : x > 0 ? "up" : "down"; }
function timeToISO(t) {
  if (typeof t === "string") return t;
  if (t && t.year) return `${t.year}-${String(t.month).padStart(2, "0")}-${String(t.day).padStart(2, "0")}`;
  return "";
}
function sparkSVG(values, w = 100, h = 30) {
  const v = values.filter((x) => x != null);
  if (v.length < 2) return "";
  const min = Math.min(...v), max = Math.max(...v), span = max - min || 1;
  const pts = v.map((x, i) =>
    `${(i / (v.length - 1) * w).toFixed(1)},${(h - 2 - (x - min) / span * (h - 4)).toFixed(1)}`
  ).join(" ");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">` +
    `<polyline points="${pts}" fill="none" stroke="${COLORS.s1}" stroke-width="1.5"/></svg>`;
}

/* ---------- データ読み込み ---------- */
async function loadJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}
async function loadSymbol(key) {
  if (!state.symCache.has(key)) {
    state.symCache.set(key, await loadJSON(`data/symbols/${key}.json`));
  }
  return state.symCache.get(key);
}

/* ---------- ヘッダー・バナー ---------- */
function renderMeta() {
  const m = state.meta;
  const isDemo = m.data_source === "seed-demo";
  const dt = new Date(m.generated_at).toLocaleString("ja-JP", { dateStyle: "medium", timeStyle: "short" });
  $("#meta-line").innerHTML =
    `データ生成: ${dt} ` +
    (isDemo ? `<span class="badge demo">デモデータ</span>` : `<span class="badge live">実データ</span>`);
  if (isDemo) {
    $("#banner").innerHTML =
      `<div class="banner-demo">⚠️ 現在表示しているのは<strong>合成デモデータ</strong>です(実際の市場価格ではありません)。` +
      `GitHub Actions の定期実行、または <code>pipeline/build.py --live</code> の実行で実データに置き換わります。</div>`;
  }
}

/* ---------- 市場概況タイル ---------- */
function renderTiles() {
  const rows = state.screener.rows.filter((r) => r.type === "index");
  $("#tiles").innerHTML = rows.map((r) => `
    <div class="tile" tabindex="0" role="button" data-sym="${r.symbol}"
         aria-label="${r.name_ja} を選択">
      <span class="label">${r.name_ja} <span style="color:var(--muted)">${r.symbol}</span></span>
      <span class="row">
        <span class="value">${fmtPrice(r.close)}</span>
        <span class="delta ${deltaClass(r.chg1d)}">${fmtPct(r.chg1d)}</span>
      </span>
      ${sparkSVG(r.spark)}
    </div>`).join("");
  document.querySelectorAll("#tiles .tile").forEach((el) => {
    const go = () => selectSymbol(el.dataset.sym);
    el.addEventListener("click", go);
    el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
  });
}

/* ---------- フィルタ行 ---------- */
function renderFilters() {
  $("#chips").innerHTML = MARKETS.map((m) =>
    `<button class="chip ${m === state.market ? "on" : ""}" data-m="${m}">${m}</button>`).join("");
  document.querySelectorAll("#chips .chip").forEach((el) =>
    el.addEventListener("click", () => { state.market = el.dataset.m; refreshFiltered(); }));

  const rows = filteredRows();
  const groups = {};
  rows.forEach((r) => (groups[r.market] ??= []).push(r));
  $("#sym-select").innerHTML = Object.entries(groups).map(([g, rs]) =>
    `<optgroup label="${g}">` +
    rs.map((r) => `<option value="${r.symbol}" ${r.symbol === state.symbol ? "selected" : ""}>${r.name_ja} (${r.symbol})</option>`).join("") +
    `</optgroup>`).join("");
}

function filteredRows() {
  return state.screener.rows.filter((r) => state.market === "すべて" || r.market === state.market);
}

function refreshFiltered() {
  const rows = filteredRows();
  if (!rows.some((r) => r.symbol === state.symbol) && rows.length) {
    state.symbol = rows[0].symbol;
  }
  renderFilters();
  renderScreener();
  loadAndRenderCharts();
}

/* ---------- メインチャート ---------- */
function baseChartOptions() {
  return {
    autoSize: true,
    layout: {
      background: { type: "solid", color: "transparent" },
      textColor: COLORS.muted, fontSize: 11,
      fontFamily: "system-ui, -apple-system, sans-serif",
      // 帰属表記はフッターのクレジットに明示(ペイン内ロゴはデータと重なるため無効化)
      attributionLogo: false,
    },
    grid: {
      vertLines: { color: COLORS.grid },
      horzLines: { color: COLORS.grid },
    },
    rightPriceScale: { borderColor: COLORS.grid },
    timeScale: { borderColor: COLORS.grid, timeVisible: false },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    localization: { locale: "ja-JP" },
  };
}

function initCharts() {
  const LC = LightweightCharts;
  const main = LC.createChart($("#chart-main"), baseChartOptions());
  const rsi = LC.createChart($("#chart-rsi"), baseChartOptions());
  const macd = LC.createChart($("#chart-macd"), baseChartOptions());
  rsi.timeScale().applyOptions({ visible: false });
  // 時間軸はMACDペイン(最下段)にのみ表示

  const candles = main.addCandlestickSeries({
    upColor: COLORS.up, downColor: COLORS.down, borderVisible: false,
    wickUpColor: COLORS.up, wickDownColor: COLORS.down,
  });
  const volume = main.addHistogramSeries({
    priceScaleId: "vol", priceFormat: { type: "volume" },
    priceLineVisible: false, lastValueVisible: false,
  });
  main.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

  const mkLine = (chart, color, width = 2) => chart.addLineSeries({
    color, lineWidth: width, priceLineVisible: false, lastValueVisible: false,
    crosshairMarkerRadius: 4,
  });
  const sma20 = mkLine(main, COLORS.s1);
  const sma50 = mkLine(main, COLORS.s2);
  const sma200 = mkLine(main, COLORS.s3);
  const bbUp = mkLine(main, COLORS.bb, 1);
  const bbMid = mkLine(main, COLORS.bb, 1);
  const bbLow = mkLine(main, COLORS.bb, 1);

  const rsiLine = mkLine(rsi, COLORS.s1);
  [30, 70].forEach((p) => rsiLine.createPriceLine({
    price: p, color: "#3a3f47", lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Solid, axisLabelVisible: true, title: "",
  }));
  const macdLine = mkLine(macd, COLORS.s1);
  const macdSig = mkLine(macd, COLORS.s2);
  const macdHist = macd.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false });

  // 3ペインの表示範囲を同期
  let syncing = false;
  const link = (a, b) => a.timeScale().subscribeVisibleLogicalRangeChange((r) => {
    if (!r || syncing) return;
    syncing = true;
    b.forEach((c) => c.timeScale().setVisibleLogicalRange(r));
    syncing = false;
  });
  link(main, [rsi, macd]); link(rsi, [main, macd]); link(macd, [main, rsi]);

  main.subscribeCrosshairMove((p) => updateReadout(timeToISO(p.time)));

  state.charts = { main, rsi, macd };
  state.series = { candles, volume, sma20, sma50, sma200, bbUp, bbMid, bbLow, rsiLine, macdLine, macdSig, macdHist };

  document.querySelectorAll(".toggles input").forEach((el) =>
    el.addEventListener("change", applyToggles));
}

function applyToggles() {
  const vis = (id) => $(`#tgl-${id}`).checked;
  const s = state.series;
  s.sma20.applyOptions({ visible: vis("sma20") });
  s.sma50.applyOptions({ visible: vis("sma50") });
  s.sma200.applyOptions({ visible: vis("sma200") });
  [s.bbUp, s.bbMid, s.bbLow].forEach((x) => x.applyOptions({ visible: vis("bb") }));
  document.querySelectorAll(".chart-legend .key[data-tgl]").forEach((el) => {
    el.style.display = vis(el.dataset.tgl) ? "" : "none";
  });
}

function lineData(bars, arr) {
  const out = [];
  for (let i = 0; i < bars.length; i++) {
    if (arr[i] != null) out.push({ time: bars[i][0], value: arr[i] });
  }
  return out;
}

async function loadAndRenderCharts() {
  const row = state.screener.rows.find((r) => r.symbol === state.symbol);
  if (!row) return;
  const d = await loadSymbol(row.key);
  const s = state.series;
  const ref = row.close;

  state.timeIndex = new Map(d.bars.map((b, i) => [b[0], i]));
  state.current = d;

  s.candles.setData(d.bars.map((b) => ({ time: b[0], open: b[1], high: b[2], low: b[3], close: b[4] })));
  s.volume.setData(d.bars.map((b) => ({
    time: b[0], value: b[5], color: b[4] >= b[1] ? COLORS.upA : COLORS.downA,
  })));
  s.sma20.setData(lineData(d.bars, d.ind.sma20));
  s.sma50.setData(lineData(d.bars, d.ind.sma50));
  s.sma200.setData(lineData(d.bars, d.ind.sma200));
  s.bbUp.setData(lineData(d.bars, d.ind.bb_up));
  s.bbMid.setData(lineData(d.bars, d.ind.bb_mid));
  s.bbLow.setData(lineData(d.bars, d.ind.bb_low));
  s.rsiLine.setData(lineData(d.bars, d.ind.rsi14));
  s.macdLine.setData(lineData(d.bars, d.ind.macd));
  s.macdSig.setData(lineData(d.bars, d.ind.macds));
  s.macdHist.setData(d.bars.map((b, i) => ({
    time: b[0], value: d.ind.macdh[i] ?? 0,
    color: (d.ind.macdh[i] ?? 0) >= 0 ? COLORS.upA : COLORS.downA,
  })));

  $("#chart-title").textContent = `${d.name_ja} (${d.symbol})`;
  applyToggles();
  updateReadout(d.bars[d.bars.length - 1][0]);
  Object.values(state.charts).forEach((c) => c.timeScale().fitContent());

  renderBacktest(row);
}

function updateReadout(iso) {
  const d = state.current;
  if (!d || !iso || !state.timeIndex.has(iso)) return;
  const i = state.timeIndex.get(iso);
  const b = d.bars[i];
  const ref = b[4];
  const chg = i > 0 ? (b[4] / d.bars[i - 1][4] - 1) * 100 : null;
  $("#readout-ohlc").innerHTML =
    `<b>${iso}</b>` +
    ` <span>始 ${fmtPrice(b[1], ref)}</span> <span>高 ${fmtPrice(b[2], ref)}</span>` +
    ` <span>安 ${fmtPrice(b[3], ref)}</span> <span>終 <b>${fmtPrice(b[4], ref)}</b></span>` +
    ` <span class="delta ${deltaClass(chg)}">${fmtPct(chg)}</span>` +
    (b[5] ? ` <span>出来高 ${fmtCompact(b[5])}</span>` : "");
  const v = (arr, dg = 2) => arr[i] == null ? "–" : arr[i].toFixed(dg);
  $("#readout-sma").innerHTML =
    `<span class="key" data-tgl="sma20"><span class="swatch line" style="background:${COLORS.s1}"></span>SMA20 ${fmtPrice(d.ind.sma20[i], ref)}</span>` +
    `<span class="key" data-tgl="sma50"><span class="swatch line" style="background:${COLORS.s2}"></span>SMA50 ${fmtPrice(d.ind.sma50[i], ref)}</span>` +
    `<span class="key" data-tgl="sma200"><span class="swatch line" style="background:${COLORS.s3}"></span>SMA200 ${fmtPrice(d.ind.sma200[i], ref)}</span>` +
    `<span class="key" data-tgl="bb"><span class="swatch line" style="background:${COLORS.bb}"></span>BB(20,2σ)</span>`;
  $("#readout-rsi").textContent = `RSI(14): ${v(d.ind.rsi14, 1)}`;
  $("#readout-macd").textContent = `MACD: ${v(d.ind.macd)} シグナル: ${v(d.ind.macds)}`;
  applyToggles();
}

/* ---------- スクリーナー ---------- */
const COLUMNS = [
  { key: "name_ja", label: "銘柄", num: false },
  { key: "market", label: "市場", num: false },
  { key: "close", label: "終値", num: true },
  { key: "chg1d", label: "前日比", num: true },
  { key: "chg5d", label: "5日", num: true },
  { key: "chg20d", label: "20日", num: true },
  { key: "rsi14", label: "RSI14", num: true },
  { key: "vs_hi52", label: "52週高値比", num: true },
  { key: "vs_lo52", label: "52週安値比", num: true },
  { key: "trend_up", label: "トレンド", num: true },
  { key: "vol_ratio", label: "出来高比", num: true },
  { key: "spark", label: "30日推移", num: false },
];

function renderScreener() {
  let rows = [...filteredRows()];
  const { key, dir } = state.sort;
  if (key) {
    rows.sort((a, b) => {
      const av = a[key], bv = b[key];
      if (av == null) return 1;
      if (bv == null) return -1;
      return (av > bv ? 1 : av < bv ? -1 : 0) * dir;
    });
  }
  $("#screener-head").innerHTML = COLUMNS.map((c) =>
    `<th class="${key === c.key ? "sorted" : ""}" data-k="${c.key}">${c.label}${key === c.key ? (dir > 0 ? " ↑" : " ↓") : ""}</th>`).join("");
  document.querySelectorAll("#screener-head th").forEach((th) =>
    th.addEventListener("click", () => {
      const k = th.dataset.k;
      state.sort = { key: k, dir: state.sort.key === k ? -state.sort.dir : -1 };
      renderScreener();
    }));

  $("#screener-body").innerHTML = rows.map((r) => {
    const rsiPill = r.rsi14 == null ? "" :
      r.rsi14 <= 30 ? `<span class="pill oversold">売られすぎ</span>` :
      r.rsi14 >= 70 ? `<span class="pill overbought">買われすぎ</span>` : "";
    const trend = r.trend_up == null ? "–" :
      r.trend_up ? `<span class="delta up">▲ 上昇</span>` : `<span class="delta down">▼ 下降</span>`;
    const gc = r.golden_cross_20d ? ` <span class="pill gc">GC</span>` : "";
    return `<tr data-sym="${r.symbol}" class="${r.symbol === state.symbol ? "sel" : ""}">
      <td class="name-cell"><span class="nm">${r.name_ja}</span><br><span class="sym-code">${r.symbol}</span></td>
      <td>${r.market}</td>
      <td class="num">${fmtPrice(r.close)}</td>
      <td class="num delta ${deltaClass(r.chg1d)}">${fmtPct(r.chg1d)}</td>
      <td class="num delta ${deltaClass(r.chg5d)}">${fmtPct(r.chg5d)}</td>
      <td class="num delta ${deltaClass(r.chg20d)}">${fmtPct(r.chg20d)}</td>
      <td class="num">${r.rsi14 ?? "–"} ${rsiPill}</td>
      <td class="num">${fmtPct(r.vs_hi52)}</td>
      <td class="num">${fmtPct(r.vs_lo52)}</td>
      <td>${trend}${gc}</td>
      <td class="num">${r.vol_ratio == null ? "–" : r.vol_ratio.toFixed(2) + "×"}</td>
      <td style="min-width:110px">${sparkSVG(r.spark, 100, 26)}</td>
    </tr>`;
  }).join("");
  document.querySelectorAll("#screener-body tr").forEach((tr) =>
    tr.addEventListener("click", () => selectSymbol(tr.dataset.sym)));
}

/* ---------- バックテスト ---------- */
function initEquityChart() {
  const opts = baseChartOptions();
  opts.localization.priceFormatter = (v) =>
    v >= 1e8 ? `${(v / 1e8).toFixed(2)}億` : `${Math.round(v / 1e4).toLocaleString("ja-JP")}万`;
  const eq = LightweightCharts.createChart($("#chart-equity"), opts);
  state.charts.equity = eq;
  state.series.eqStrats = {};
  for (const [sid, color] of Object.entries(STRAT_COLORS)) {
    state.series.eqStrats[sid] = eq.addLineSeries({
      color, lineWidth: 2, priceLineVisible: false, lastValueVisible: false,
    });
  }
  state.series.eqBH = eq.addLineSeries({
    color: COLORS.baseline, lineWidth: 2, priceLineVisible: false, lastValueVisible: false,
  });
}

function renderBacktest(row) {
  const bt = state.backtests.results.find((x) => x.symbol === row.symbol);
  const wrap = $("#bt-cards");
  if (!bt) { wrap.innerHTML = `<p class="section-desc">この銘柄のバックテスト結果はありません。</p>`; return; }

  $("#bt-title").textContent = `${bt.name_ja} (${bt.symbol}) — 初期資金 ${fmtCompact(state.backtests.cash)}・手数料 ${(state.backtests.commission * 100).toFixed(1)}%`;
  wrap.innerHTML = bt.strategies.map((st) => `
    <div class="bt-card">
      <h3><span class="swatch line" style="background:${STRAT_COLORS[st.id]};width:14px;height:3px;border-radius:2px;display:inline-block"></span>${st.name_ja}</h3>
      <div class="headline delta ${deltaClass(st.return_pct)}">${fmtPct(st.return_pct)}</div>
      <dl class="stat-grid">
        <dt>バイ&ホールド</dt><dd class="delta ${deltaClass(st.buy_hold_pct)}">${fmtPct(st.buy_hold_pct)}</dd>
        <dt>シャープレシオ</dt><dd>${st.sharpe ?? "–"}</dd>
        <dt>ソルティノレシオ</dt><dd>${st.sortino ?? "–"}</dd>
        <dt>最大ドローダウン</dt><dd>${st.max_dd_pct == null ? "–" : st.max_dd_pct + "%"}</dd>
        <dt>CAGR(年率)</dt><dd>${st.cagr_pct == null ? "–" : st.cagr_pct + "%"}</dd>
        <dt>取引回数</dt><dd>${st.trades}</dd>
        <dt>勝率</dt><dd>${st.win_rate == null ? "–" : st.win_rate.toFixed(1) + "%"}</dd>
      </dl>
    </div>`).join("");

  for (const st of bt.strategies) {
    state.series.eqStrats[st.id].setData(st.equity.map(([t, v]) => ({ time: t, value: v })));
  }
  // バイ&ホールド曲線は保有バーから算出(同一開始日・同一初期資金)
  const d = state.current;
  const t0 = bt.strategies[0].equity[0][0];
  const bars = d.bars.filter((b) => b[0] >= t0);
  if (bars.length) {
    const c0 = bars[0][4];
    state.series.eqBH.setData(bars.map((b) => ({ time: b[0], value: state.backtests.cash * b[4] / c0 })));
  } else {
    state.series.eqBH.setData([]);
  }
  state.charts.equity.timeScale().fitContent();
}

/* ---------- シンボル選択 ---------- */
function selectSymbol(sym) {
  state.symbol = sym;
  renderFilters();
  renderScreener();
  loadAndRenderCharts();
  $("#chart-section").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* ---------- 初期化 ---------- */
async function init() {
  try {
    const [meta, screener, backtests, repos] = await Promise.all([
      loadJSON("data/meta.json"), loadJSON("data/screener.json"),
      loadJSON("data/backtests.json"), loadJSON("data/repos.json"),
    ]);
    Object.assign(state, { meta, screener, backtests });
    state.symbol = screener.rows[0]?.symbol;

    renderMeta();
    renderTiles();
    renderFilters();
    initCharts();
    initEquityChart();
    renderScreener();
    $("#sym-select").addEventListener("change", (e) => selectSymbol(e.target.value));

    $("#repo-summary").innerHTML =
      `収録 <b>${repos.count}</b> リポジトリ / ` +
      Object.entries(repos.categories).map(([k, v]) =>
        `${v} ${repos.repos.filter((r) => r.category === k).length}`).join("・");

    await loadAndRenderCharts();
  } catch (e) {
    $("#banner").innerHTML =
      `<div class="banner-demo">データの読み込みに失敗しました(${e.message})。` +
      `ローカルで開く場合は <code>python3 -m http.server</code> などのHTTPサーバー経由でアクセスしてください。</div>`;
    console.error(e);
  }
}

document.addEventListener("DOMContentLoaded", init);
