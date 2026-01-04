# 飞书机器人邮件转发服务启动脚本（长连接模式）- PowerShell版本

# 设置字符编码为UTF-8（解决中文乱码）
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "飞书机器人邮件转发服务（长连接模式）" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python版本: $pythonVersion" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "错误: 未检测到Python，请先安装Python 3.9或更高版本" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

# 检查并创建虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "创建Python虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: 创建虚拟环境失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
    Write-Host "虚拟环境创建成功" -ForegroundColor Green
    Write-Host ""
}

# 激活虚拟环境
Write-Host "激活虚拟环境..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 激活虚拟环境失败" -ForegroundColor Red
    Write-Host "提示: 如果遇到执行策略错误，请以管理员身份运行PowerShell并执行:" -ForegroundColor Yellow
    Write-Host "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}
Write-Host ""

# 检查是否需要安装依赖
if ($args[0] -eq "install") {
    Write-Host "安装Python依赖..." -ForegroundColor Yellow
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    Write-Host ""
    Write-Host "依赖安装完成" -ForegroundColor Green
    Read-Host "按回车键退出"
    exit 0
}

# 检查依赖是否已安装
$flaskInstalled = pip show Flask 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "检测到依赖未安装，正在安装..." -ForegroundColor Yellow
    pip install -r requirements.txt
    Write-Host ""
}

# 检查.env文件是否存在
if (-not (Test-Path ".env")) {
    Write-Host "错误: .env 文件不存在" -ForegroundColor Red
    Write-Host "请先复制 .env.example 为 .env 并配置相关信息" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

# 启动长连接服务
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "启动飞书机器人（长连接模式）" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "提示: 按 Ctrl+C 可停止服务" -ForegroundColor Yellow
Write-Host ""

# 运行主程序
try {
    python app_ws.py
} catch {
    Write-Host ""
    Write-Host "服务异常退出" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
} finally {
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "服务异常退出，错误代码: $LASTEXITCODE" -ForegroundColor Red
        Read-Host "按回车键退出"
    }
}
