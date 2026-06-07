# 一键启动脚本 - 后端 + 前端（开发模式）
# 在 PyCharm 中运行此脚本，或双击运行

Write-Output "=== AI智能测试大屏平台 - 一键启动（开发模式）==="
Write-Output ""

# ============ 配置 ============
$backendPath = "D:\WorkCode\AiTest\MGTV_Ai_Agent\backend"
$frontendPath = "D:\WorkCode\AiTest\MGTV_Ai_Agent\frontend"
$venvActivate = "D:\WorkCode\AiTest\MGTV_Ai_Agent\.venv\Scripts\Activate.ps1"

# ============ 检查依赖 ============
Write-Output "1. 检查依赖..."

# 检查后端虚拟环境
if (-not (Test-Path $venvActivate)) {
    Write-Output "❌ 虚拟环境不存在: $venvActivate"
    Write-Output "   请先运行: python -m venv .venv"
    pause
    exit 1
}
Write-Output "   ✅ 后端虚拟环境存在"

# 检查前端依赖
if (-not (Test-Path "$frontendPath\node_modules")) {
    Write-Output "   ⚠️ 前端依赖未安装，正在安装..."
    Set-Location $frontendPath
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Output "   ❌ 前端依赖安装失败"
        pause
        exit 1
    }
}
Write-Output "   ✅ 前端依赖已安装"

Write-Output ""
Write-Output "2. 启动服务..."

# ============ 启动后端 ============
Write-Output "   → 启动后端 (FastAPI:8000)..."
$backendJob = Start-Process powershell.exe `
    -ArgumentList "-NoExit", "-Command", "& '$venvActivate'; cd '$backendPath'; python main.py" `
    -PassThru

Start-Sleep -Seconds 3

# 检查后端是否启动成功
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Output "   ✅ 后端启动成功: http://localhost:8000"
} catch {
    Write-Output "   ❌ 后端启动失败，请检查日志"
}

# ============ 启动前端 ============
Write-Output "   → 启动前端 (Vite:3000)..."
$frontendJob = Start-Process powershell.exe `
    -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev" `
    -PassThru

Start-Sleep -Seconds 5

# ============ 打开浏览器 ============
Write-Output ""
Write-Output "3. 打开浏览器..."
Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"

Write-Output ""
Write-Output "=== 启动完成 ==="
Write-Output "前端界面: http://localhost:3000 (Vite 热更新)"
Write-Output "后端 API: http://localhost:8000"
Write-Output "API 文档: http://localhost:8000/docs"
Write-Output ""
Write-Output "提示："
Write-Output "  - 后端日志在窗口 1"
Write-Output "  - 前端日志在窗口 2"
Write-Output "  - 修改前端代码会自动刷新（热更新）"
Write-Output "  - 关闭窗口即可停止服务"
Write-Output ""
Write-Output "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
