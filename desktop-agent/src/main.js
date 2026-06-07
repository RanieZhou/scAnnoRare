// scAnnoRare Local Agent desktop shell — status panel logic

const AGENT = "http://127.0.0.1:17890";

let statusDot, statusText, pairState, genBtn, codeBox, countdownEl;
let countdownTimer = null;
let hwFetched = false;

async function checkHealth() {
  try {
    const res = await fetch(`${AGENT}/api/v1/local/health`, { cache: "no-store" });
    const data = await res.json();
    setOnline(true, data.paired);
    if (!hwFetched) fetchHardware();
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

async function fetchHardware() {
  try {
    const res = await fetch(`${AGENT}/api/v1/local/admin/hardware`, { cache: "no-store" });
    if (!res.ok) return;
    const d = await res.json();
    hwFetched = true;

    const cpu = d.cpu || {};
    const cpuName = cpu.name || cpu.architecture || "Unknown";
    const cores = cpu.logical_cores ? ` · ${cpu.logical_cores} cores` : "";
    document.getElementById("hw-cpu").textContent = cpuName + cores;

    const gpus = d.gpu_devices || [];
    if (gpus.length > 0) {
      const names = gpus.map((g) => {
        const vram = g.memory_total_gb ? ` (${g.memory_total_gb} GB)` : "";
        return g.name + vram;
      });
      document.getElementById("hw-gpu").textContent = names.join(", ");
    } else {
      document.getElementById("hw-gpu").textContent = "No CUDA GPU detected";
      document.getElementById("hw-gpu").style.color = "var(--muted)";
    }

    if (d.memory_gb) {
      document.getElementById("hw-ram").textContent = `${d.memory_gb} GB`;
    }
  } catch {
    // hardware fetch failed silently — non-critical
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
