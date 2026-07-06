/* OSSレジストリ・カタログページ */
"use strict";

const state = { data: null, cat: "all", q: "" };
const $ = (sel) => document.querySelector(sel);

function render() {
  const { categories, repos } = state.data;
  const q = state.q.toLowerCase();
  const rows = repos.filter((r) =>
    (state.cat === "all" || r.category === state.cat) &&
    (!q || `${r.owner}/${r.repo} ${r.desc_ja} ${r.lang ?? ""}`.toLowerCase().includes(q))
  );
  // 「使用中」を先頭に
  rows.sort((a, b) => (b.used_in_app ? 1 : 0) - (a.used_in_app ? 1 : 0));

  $("#count-note").textContent = `${rows.length} 件を表示(全 ${repos.length} 件)`;
  $("#grid").innerHTML = rows.map((r) => `
    <div class="repo-card">
      <div class="top">
        <a class="rname" href="${r.url}" target="_blank" rel="noopener">${r.owner}/${r.repo}</a>
        <span class="cat">${categories[r.category]}</span>
        ${r.used_in_app ? `<span class="used">本アプリで使用中</span>` : ""}
      </div>
      <p class="desc">${r.desc_ja}</p>
      <div class="foot">
        ${r.lang && r.lang !== "-" ? `<span>${r.lang}</span>` : ""}
        ${r.license && r.license !== "-" ? `<span>${r.license}</span>` : ""}
      </div>
    </div>`).join("");
}

function renderChips() {
  const { categories, repos } = state.data;
  const counts = {};
  repos.forEach((r) => counts[r.category] = (counts[r.category] ?? 0) + 1);
  const chips = [["all", `すべて (${repos.length})`]]
    .concat(Object.entries(categories).map(([k, v]) => [k, `${v} (${counts[k] ?? 0})`]));
  $("#cat-chips").innerHTML = chips.map(([k, label]) =>
    `<button class="chip ${state.cat === k ? "on" : ""}" data-c="${k}">${label}</button>`).join("");
  document.querySelectorAll("#cat-chips .chip").forEach((el) =>
    el.addEventListener("click", () => { state.cat = el.dataset.c; renderChips(); render(); }));
}

async function init() {
  const r = await fetch("data/repos.json");
  state.data = await r.json();
  renderChips();
  render();
  $("#q").addEventListener("input", (e) => { state.q = e.target.value; render(); });
}

document.addEventListener("DOMContentLoaded", init);
