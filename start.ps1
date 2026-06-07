# 一键启动脚本 - AI智能测试大屏平台
# 启动后端（FastAPI）和前端（React）

Write-Output "=== AI智能测试大屏平台 - 一键启动 ==="
Write-Output ""

# 检查 backend 虚拟环境
$venvPath = "D:\WorkCode\AiTest\MGTV_Ai_Agent\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvPath)) {
    Write-Output "❌ 虚拟环境不存在: $venvPath"
    Write-Output "   请先运行: python -m venv .venv"
    pause
    exit 1
}

# 检查 frontend 依赖
$frontendNodeModules = "D:\WorkCode\AiTest\MGTV_Ai_Agent\frontend\node_modules"
if (-not (Test-Path $frontendNodeModules)) {
    Write-Output "⚠️ 前端依赖未安装，正在安装..."
    Set-Location "D:\WorkCode\AiTest\MGTV_Ai_Agent\frontend"
    npm install
}

# 启动后端（新窗口）
Write-Output "1. 启动后端服务 (FastAPI:8000)..."
$backendJob = Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "& '$venvPath'; cd D:\WorkCode\AiTest\MGTV_Ai_Agent\backend; python main.py" -PassThru

Start-Sleep -Seconds 3

# 检查后端是否启动成功
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Output "✅ 后端启动成功: http://localhost:8000"
    Write-Output "   API 文档: http://localhost:8000/docs"
} catch {
    Write-Output "❌ 后端启动失败，请检查日志"
}

# 构建前端（如果 dist 目录不存在）
$distPath = "D:\WorkCode\AiTest\MGTV_Ai_Agent\frontend\dist"
if (-not (Test-Path $distPath)) {
    Write-Output ""
    Write-Output "2. 构建前端（首次需要 2-5 分钟）..."
    Set-Location "D:\WorkCode\AiTest\MGTV_Ai_Agent\frontend"
    npm run build
    
    if ($LASTEXITCODE -eq 0) {
        Write-Output "✅ 前端构建完成"
    } else {
        Write-Output "❌ 前端构建失败"
    }
} else {
    Write-Output "✅ 前端已构建: $distPath"
}

# 打开浏览器
Write-Output ""
Write-Output "3. 打开浏览器..."
Start-Sleep -Seconds 2
Start-Process "http://localhost:8000"

Write-Output ""
Write-Output "=== 启动完成 ==="
Write-Output "前端界面: http://localhost:8000"
Write-Output "API 文档: http://localhost:8000/docs"
Write-Output ""
Write-Output "提示："
Write-Output "  - 后端日志在当前窗口"
Write-Output "  - 关闭窗口即可停止服务"
Write-Output "  - 前端修改后需重新构建: cd frontend && npm run build"
Write-Output ""
Write-Output "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
