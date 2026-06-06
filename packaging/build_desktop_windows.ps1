# scAnnoRare 桌面应用一键打包脚本（Windows）
# 产出：自带桥接 Agent 的 .msi / .exe 安装包
# 注意：计算依赖不打进安装包，用户需在本机选择已有 Python 环境。
#
# 前置（需在 Windows 机器上预装）：
#   - Python 3.10/3.11      https://www.python.org/
#   - Node.js 18+           https://nodejs.org/
#   - Rust (stable)         https://rustup.rs/
#   - Microsoft C++ Build Tools（含 MSVC）
#   - WebView2 Runtime（Win11 自带；Win10 可能需手动安装）
#
# 用法（在仓库根目录 PowerShell 执行）：
#   powershell -ExecutionPolicy Bypass -File packaging\build_desktop_windows.ps1

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..").Path
Write-Host "==> 仓库根目录: $Root" -ForegroundColor Cyan

# ── 1. 打包 Local Agent（PyInstaller，产出 scannorare-agent.exe）──────────────
Write-Host "`n[1/3] 打包 Local Agent ..." -ForegroundColor Green
Set-Location "$Root\local-agent"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
Set-Location "$Root\local-agent\packaging"
Remove-Item -Recurse -Force .\dist\scannorare-agent -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\build -ErrorAction SilentlyContinue
pyinstaller agent.spec --distpath .\dist --workpath .\build --noconfirm
if (-not (Test-Path ".\dist\scannorare-agent\scannorare-agent.exe")) {
    throw "Agent 打包失败：未找到 dist\scannorare-agent\scannorare-agent.exe"
}
Write-Host "    Agent 打包完成: dist\scannorare-agent\scannorare-agent.exe" -ForegroundColor Green

# ── 2. 安装前端依赖 ───────────────────────────────────────────────────────────
Write-Host "`n[2/3] 安装桌面壳依赖 ..." -ForegroundColor Green
Set-Location "$Root\desktop-agent"
npm install

# ── 3. 构建 Tauri 安装包（自动把 Agent 作为 resource 打入）─────────────────────
Write-Host "`n[3/3] 构建 Tauri 安装包 ..." -ForegroundColor Green
npm run tauri build

Write-Host "`n==> 完成！安装包位于：" -ForegroundColor Cyan
Write-Host "    desktop-agent\src-tauri\target\release\bundle\msi\   (.msi)"
Write-Host "    desktop-agent\src-tauri\target\release\bundle\nsis\  (.exe)"
