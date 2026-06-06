#!/usr/bin/env bash
# scAnnoRare 桌面应用一键打包脚本（macOS）
# 产出：自带桥接 Agent 的 .app / .dmg
# 注意：计算依赖不打进安装包，用户需在本机选择已有 Python 环境。
#
# 前置（需预装）：
#   - Python 3.10/3.11
#   - Node.js 18+
#   - Rust (stable)            https://rustup.rs/
#   - Xcode Command Line Tools （xcode-select --install）
#
# 用法（在仓库根目录执行）：
#   bash packaging/build_desktop_macos.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "==> 仓库根目录: $ROOT"
source "$HOME/.cargo/env" 2>/dev/null || true

# ── 1. 打包 Local Agent（PyInstaller，产出 scannorare-agent）───────────────────
echo ""
echo "[1/3] 打包 Local Agent ..."
cd "$ROOT/local-agent"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller
cd "$ROOT/local-agent/packaging"
rm -rf ./dist/scannorare-agent ./build
pyinstaller agent.spec --distpath ./dist --workpath ./build --noconfirm
test -f "./dist/scannorare-agent/scannorare-agent" \
  || { echo "Agent 打包失败"; exit 1; }
echo "    Agent 打包完成: dist/scannorare-agent/scannorare-agent"

# ── 2. 安装前端依赖 ───────────────────────────────────────────────────────────
echo ""
echo "[2/3] 安装桌面壳依赖 ..."
cd "$ROOT/desktop-agent"
npm install

# ── 3. 构建 Tauri 安装包（自动把 Agent 作为 resource 打入）─────────────────────
echo ""
echo "[3/3] 构建 Tauri 安装包 ..."
npm run tauri build

echo ""
echo "==> 完成！安装包位于："
echo "    desktop-agent/src-tauri/target/release/bundle/macos/   (.app)"
echo "    desktop-agent/src-tauri/target/release/bundle/dmg/     (.dmg)"
