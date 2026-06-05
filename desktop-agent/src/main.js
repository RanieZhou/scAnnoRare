// scAnnoRare Local Agent 桌面外壳 — 状态面板逻辑
// 直接 fetch 本地 Agent（Agent 放行所有 CORS；webview 非 HTTPS，无 mixed-content 问题）

const AGENT = "http://127.0.0.1:17890";

let statusDot, statusText, pairState, genBtn, codeBox, countdownEl;
let countdownTimer = null;

async function checkHealth() {
  try {
    const res = await fetch(`${AGENT}/api/v1/local/health`, { cache: "no-store" });
    const data = await res.json();
    setOnline(true, data.paired);
  } catch {
    setOnline(false, false);
  }
}

function setOnline(online, paired) {
  if (online) {
    statusDot.className = "dot online";
    statusText.textContent = "本地服务运行中";
    pairState.textContent = paired ? "已配对" : "未配对";
    pairState.className = paired ? "ok" : "warn";
    genBtn.disabled = false;
  } else {
    statusDot.className = "dot offline";
    statusText.textContent = "正在等待本地服务启动…";
    pairState.textContent = "—";
    pairState.className = "";
    genBtn.disabled = true;
  }
}

async function generateCode() {
  genBtn.disabled = true;
  try {
    const res = await fetch(`${AGENT}/api/v1/local/admin/generate-pairing-code`, {
      method: "POST",
    });
    const data = await res.json();
    showCode(data.pairing_code, data.expires_in || 300);
  } catch {
    codeBox.innerHTML = `<span class="code-placeholder err">生成失败，请确认服务已就绪</span>`;
  } finally {
    genBtn.disabled = false;
  }
}

function showCode(code, seconds) {
  codeBox.innerHTML = code
    .split("")
    .map((c) => `<span class="digit">${c}</span>`)
    .join("");
  if (countdownTimer) clearInterval(countdownTimer);
  let left = seconds;
  const tick = () => {
    countdownEl.textContent = left > 0 ? `有效期剩余 ${left} 秒` : "配对码已过期，请重新生成";
    if (left <= 0) {
      clearInterval(countdownTimer);
      codeBox.classList.add("expired");
    }
    left--;
  };
  codeBox.classList.remove("expired");
  tick();
  countdownTimer = setInterval(tick, 1000);
}

window.addEventListener("DOMContentLoaded", () => {
  statusDot = document.querySelector("#status-dot");
  statusText = document.querySelector("#status-text");
  pairState = document.querySelector("#pair-state");
  genBtn = document.querySelector("#gen-btn");
  codeBox = document.querySelector("#code-box");
  countdownEl = document.querySelector("#countdown");

  genBtn.addEventListener("click", generateCode);

  checkHealth();
  setInterval(checkHealth, 2000);
});
