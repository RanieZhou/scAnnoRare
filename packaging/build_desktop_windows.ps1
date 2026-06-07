# scAnnoRare Desktop App - Windows Build Script
# Output: .msi / .exe installer bundling the bridge agent
# Note: Scientific computing dependencies are NOT bundled.
#       Users select their own local Python environment at runtime.
#
# Prerequisites (install on Windows before running):
#   - Python 3.10 or 3.11    https://www.python.org/
#   - Node.js 18+            https://nodejs.org/
#   - Rust (stable)          https://rustup.rs/
#   - Microsoft C++ Build Tools (MSVC)
#   - WebView2 Runtime (built-in on Win11; may need manual install on Win10)
#
# Usage (run from repo root in PowerShell):
#   powershell -ExecutionPolicy Bypass -File packaging\build_desktop_windows.ps1

$ErrorActionPreference = "Stop"

# Force UTF-8 console output to prevent encoding errors on non-UTF-8 systems
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$Root = (Resolve-Path "$PSScriptRoot\..").Path
$StartTime = Get-Date
Write-Host "==> Repository root: $Root" -ForegroundColor Cyan
Write-Host "==> Build started : $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan

# ── Prerequisite checks ─────────────────────────────────────────────────────────
Write-Host "`n[PRE] Checking prerequisites ..." -ForegroundColor Yellow
$Missing = @()
foreach ($cmd in @("python", "node", "npm", "cargo")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        $Missing += $cmd
    }
}
if ($Missing.Count -gt 0) {
    Write-Host "    ERROR: The following tools were not found in PATH: $($Missing -join ', ')" -ForegroundColor Red
    Write-Host "    Please install them and re-run this script." -ForegroundColor Red
    exit 1
}
Write-Host "    All prerequisites found." -ForegroundColor Green

# ── 1. Package Local Agent (PyInstaller -> onedir exe) ─────────────────────────
Write-Host "`n[1/3] Packaging Local Agent (PyInstaller) ..." -ForegroundColor Green
Set-Location "$Root\local-agent"
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
python -m pip install pyinstaller --quiet
Set-Location "$Root\local-agent\packaging"
Remove-Item -Recurse -Force .\dist\scannorare-agent -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\build -ErrorAction SilentlyContinue
pyinstaller agent.spec --distpath .\dist --workpath .\build --noconfirm

$AgentExe = ".\dist\scannorare-agent\scannorare-agent.exe"
if (-not (Test-Path $AgentExe)) {
    Write-Host "    ERROR: Agent build failed - expected file not found: $AgentExe" -ForegroundColor Red
    exit 1
}
Write-Host "    Agent built: $AgentExe" -ForegroundColor Green

# ── 2. Install desktop shell (Tauri) dependencies ──────────────────────────────
Write-Host "`n[2/3] Installing desktop shell dependencies ..." -ForegroundColor Green
Set-Location "$Root\desktop-agent"
npm install

# ── 3. Build Tauri installer (agent bundled as sidecar resource) ────────────────
Write-Host "`n[3/3] Building Tauri installer ..." -ForegroundColor Green
npm run tauri build

$Elapsed = [math]::Round(((Get-Date) - $StartTime).TotalSeconds)
Write-Host ""
Write-Host "==> Build complete in ${Elapsed}s" -ForegroundColor Cyan
Write-Host "    Installers:"
Write-Host "      desktop-agent\src-tauri\target\release\bundle\msi\   (.msi)"
Write-Host "      desktop-agent\src-tauri\target\release\bundle\nsis\  (.exe)"
