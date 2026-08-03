# 5 年后的我 · 本地一键启动脚本
# 启动后端（FastAPI + ChromaDB）和前端（Vite dev server）
# 用法：在项目根目录执行  .\start.ps1

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

# 运行时路径（按实际安装位置，如不同请修改这两行）
$pyPath = "E:\runtimes\python312;E:\runtimes\python312\Scripts"
$nodePath = "E:\runtimes\nodejs"

Write-Host "启动后端..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "`$env:PATH='$pyPath;'+`$env:PATH; " + `
    "`$env:HF_HUB_OFFLINE='1'; `$env:TRANSFORMERS_OFFLINE='1'; `$env:HF_ENDPOINT='https://hf-mirror.com'; " + `
    "Set-Location '$backend'; uvicorn app.main:app --host 127.0.0.1 --port 8000"

Write-Host "启动前端..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "`$env:PATH='$nodePath;'+`$env:PATH; " + `
    "Set-Location '$frontend'; npm run dev"

Write-Host ""
Write-Host "后端: http://localhost:8000  (API 文档: /docs)" -ForegroundColor Cyan
Write-Host "前端: http://localhost:5173  (浏览器打开这个)" -ForegroundColor Cyan
Write-Host ""
Write-Host "首次启动后端约需 30-40 秒加载 embedding 模型，看到 'Startup done' 即可。" -ForegroundColor Yellow
Write-Host "关闭弹出的两个窗口即可停止服务。" -ForegroundColor Yellow
