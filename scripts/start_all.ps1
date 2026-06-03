# scAnnoRare one-click development launcher
Write-Host "🔮 Starting scAnnoRare baseline evaluation platform..." -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = (Resolve-Path "$ScriptDir\..").Path

# 1. Spawn Web Backend
Write-Host "🚀 Launching Web Backend on port 8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BaseDir\web-backend'; uvicorn app.main:app --host 127.0.0.1 --port 8000" -WindowStyle Normal

# 2. Spawn Local Agent
Write-Host "⚡ Launching Local Agent on port 17890..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BaseDir\local-agent'; uvicorn main:app --host 127.0.0.1 --port 17890" -WindowStyle Normal

# 3. Spawn Web Frontend
Write-Host "🌐 Launching Vue 3 SPA frontend on port 5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BaseDir\web-frontend'; npm run dev" -WindowStyle Normal

Write-Host "🎉 All services triggered successfully!" -ForegroundColor Magenta
Write-Host "- Central Web Platform: http://localhost:5173" -ForegroundColor Yellow
Write-Host "- Local Agent Server: http://127.0.0.1:17890" -ForegroundColor Yellow
