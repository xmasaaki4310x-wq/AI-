/* 簡易パスワードゲート(クライアント側)。
 *
 * 注意: 静的サイトのため完全なアクセス制御ではない。data/*.json や db/paper.db
 * のURLを直接知っていれば内容は読めてしまう。検索エンジンからの流入・偶然の
 * 訪問者を防ぐための簡易的な目隠しとして機能する。
 *
 * PASSWORD_HASH は平文パスワードのSHA-256。変更したい場合はブラウザのコンソールで
 *   crypto.subtle.digest('SHA-256', new TextEncoder().encode('新しいパスワード'))
 *     .then(b => console.log([...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('')))
 * を実行し、出力された16進文字列に置き換える。
 */
(function () {
  const PASSWORD_HASH = "f553fbfbf189b7affb949a80d82a4dc19e27ad47ea22e235aaaf4d1c829c2312";
  const SESSION_KEY = "gate_ok_v1";

  async function sha256Hex(text) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  function showGate() {
    document.documentElement.style.visibility = "hidden";
    const overlay = document.createElement("div");
    overlay.id = "gate-overlay";
    overlay.innerHTML = `
      <div class="gate-box">
        <p class="gate-title">🔒 Private</p>
        <p class="gate-desc">このページは非公開です。パスワードを入力してください。</p>
        <input type="password" id="gate-input" autocomplete="off" autofocus>
        <button id="gate-submit">開く</button>
        <p class="gate-error" id="gate-error"></p>
      </div>`;
    const style = document.createElement("style");
    style.textContent = `
      html, body { margin:0; }
      #gate-overlay {
        position: fixed; inset: 0; z-index: 99999; visibility: visible !important;
        background: #0b0e11; display: flex; align-items: center; justify-content: center;
        font-family: system-ui, -apple-system, "Hiragino Sans", sans-serif;
      }
      #gate-overlay * { visibility: visible !important; }
      #gate-overlay .gate-box {
        background: #12161c; border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px; padding: 32px 36px; width: 300px; text-align: center;
      }
      #gate-overlay .gate-title { font-size: 20px; margin: 0 0 6px; color: #e8ebee; }
      #gate-overlay .gate-desc { font-size: 13px; color: #aab2bb; margin: 0 0 16px; }
      #gate-overlay input {
        width: 100%; padding: 8px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.15);
        background: #181d24; color: #e8ebee; font-size: 14px; box-sizing: border-box; margin-bottom: 10px;
      }
      #gate-overlay button {
        width: 100%; padding: 9px; border-radius: 6px; border: none;
        background: #3987e5; color: #fff; font-weight: 600; cursor: pointer; font-size: 14px;
      }
      #gate-overlay button:hover { background: #2f74c4; }
      #gate-overlay .gate-error { color: #e66767; font-size: 12px; min-height: 16px; margin: 8px 0 0; }
    `;
    document.head.appendChild(style);
    document.body.appendChild(overlay);

    const input = overlay.querySelector("#gate-input");
    const errorEl = overlay.querySelector("#gate-error");
    async function tryUnlock() {
      const hash = await sha256Hex(input.value);
      if (hash === PASSWORD_HASH) {
        sessionStorage.setItem(SESSION_KEY, "1");
        overlay.remove();
        style.remove();
        document.documentElement.style.visibility = "";
      } else {
        errorEl.textContent = "パスワードが違います";
        input.value = "";
        input.focus();
      }
    }
    overlay.querySelector("#gate-submit").addEventListener("click", tryUnlock);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") tryUnlock(); });
  }

  if (sessionStorage.getItem(SESSION_KEY) !== "1") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", showGate);
    } else {
      showGate();
    }
  }
})();
