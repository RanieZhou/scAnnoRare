#!/usr/bin/env bash
# scAnnoRare Desktop App - macOS Build Script
# Output: .app / .dmg bundling the bridge agent
# Note: Scientific computing dependencies are NOT bundled.
#       Users select their own local Python environment at runtime.
#
# Prerequisites:
#   - Python 3.10 or 3.11
#   - Node.js 18+
#   - Rust (stable)              https://rustup.rs/
#   - Xcode Command Line Tools   (xcode-select --install)
#
# Usage (run from repo root):
#   bash packaging/build_desktop_macos.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
START_TIME=$(date +%s)
echo "==> Repository root: $ROOT"
echo "==> Build started"
source "$HOME/.cargo/env" 2>/dev/null || true

# ── Prerequisite checks ─────────────────────────────────────────────────────────
echo ""
echo "[PRE] Checking prerequisites ..."
MISSING=()
for cmd in python3 node npm cargo; do
    if ! command -v "$cmd" &>/dev/null; then
        MISSING+=("$cmd")
    fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
    echo "    ERROR: The following tools were not found in PATH: ${MISSING[*]}"
    echo "    Please install them and re-run this script."
    exit 1
fi
echo "    All prerequisites found."

# ── 1. Package Local Agent (PyInstaller -> onedir binary) ──────────────────────
echo ""
echo "[1/3] Packaging Local Agent (PyInstaller) ..."
cd "$ROOT/local-agent"
python3 -m pip install --upgrade pip --quiet
python3 -m pip install -r requirements.txt --quiet
python3 -m pip install pyinstaller --quiet
cd "$ROOT/local-agent/packaging"
rm -rf ./dist/scannorare-agent ./build
pyinstaller agent.spec --distpath ./dist --workpath ./build --noconfirm
test -f "./dist/scannorare-agent/scannorare-agent" \
  || { echo "ERROR: Agent build failed - dist/scannorare-agent/scannorare-agent not found."; exit 1; }
echo "    Agent built: dist/scannorare-agent/scannorare-agent"

# ── 2. Install desktop shell (Tauri) dependencies ──────────────────────────────
echo ""
echo "[2/3] Installing desktop shell dependencies ..."
cd "$ROOT/desktop-agent"
npm install

# ── 3. Build Tauri installer (agent bundled as sidecar resource) ────────────────
echo ""
echo "[3/3] Building Tauri installer ..."
npm run tauri build

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo ""
echo "==> Build complete in ${ELAPSED}s"
echo "    Installers:"
echo "      desktop-agent/src-tauri/target/release/bundle/macos/   (.app)"
echo "      desktop-agent/src-tauri/target/release/bundle/dmg/     (.dmg)"
