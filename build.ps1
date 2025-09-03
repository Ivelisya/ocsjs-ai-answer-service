# Windows PowerShell 脚本 - 替代 Makefile

# 激活虚拟环境
function Activate-Venv {
    if (Test-Path "venv\Scripts\activate.ps1") {
        & "venv\Scripts\activate.ps1"
        Write-Host "虚拟环境已激活" -ForegroundColor Green
    }
    elseif (Test-Path "venv\bin\activate.ps1") {
        & "venv\bin\activate.ps1"
        Write-Host "虚拟环境已激活" -ForegroundColor Green
    }
    else {
        Write-Host "未找到虚拟环境，请先运行: python -m venv venv" -ForegroundColor Yellow
    }
}

# 安装生产依赖
function Install-Production {
    Write-Host "安装生产依赖..." -ForegroundColor Cyan
    pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "生产依赖安装成功！" -ForegroundColor Green
    }
    else {
        Write-Host "生产依赖安装失败！" -ForegroundColor Red
    }
}

# 安装开发依赖
function Install-Development {
    Write-Host "安装开发依赖..." -ForegroundColor Cyan
    pip install -r requirements.txt
    pip install black isort flake8 mypy pre-commit pytest pytest-asyncio
    if ($LASTEXITCODE -eq 0) {
        Write-Host "开发依赖安装成功！" -ForegroundColor Green
    }
    else {
        Write-Host "开发依赖安装失败！" -ForegroundColor Red
    }
}

# 运行测试
function Run-Tests {
    Write-Host "运行测试..." -ForegroundColor Cyan
    pytest tests/ -v --cov=app --cov=utils --cov-report=html
    if ($LASTEXITCODE -eq 0) {
        Write-Host "测试运行完成！" -ForegroundColor Green
    }
    else {
        Write-Host "测试运行失败！" -ForegroundColor Red
    }
}

# 代码检查
function Run-Lint {
    Write-Host "运行代码检查..." -ForegroundColor Cyan
    flake8 app.py utils.py models.py config.py prompts.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "代码检查通过！" -ForegroundColor Green
    }
    else {
        Write-Host "代码检查失败！" -ForegroundColor Red
    }
}

# 代码格式化
function Run-Format {
    Write-Host "格式化代码..." -ForegroundColor Cyan
    black app.py utils.py models.py config.py prompts.py
    isort app.py utils.py models.py config.py prompts.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "代码格式化完成！" -ForegroundColor Green
    }
    else {
        Write-Host "代码格式化失败！" -ForegroundColor Red
    }
}

# 清理缓存文件
function Clean-Cache {
    Write-Host "清理缓存文件..." -ForegroundColor Cyan
    Get-ChildItem -Path . -Recurse -Include "*.pyc" -File | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -Include "__pycache__" -Directory | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Include "*.egg-info" -Directory | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Include ".coverage" -File | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -Include "htmlcov" -Directory | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Include ".pytest_cache" -Directory | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Include ".mypy_cache" -Directory | Remove-Item -Recurse -Force
    Write-Host "缓存清理完成！" -ForegroundColor Green
}

# 初始化数据库
function Init-Database {
    Write-Host "初始化数据库..." -ForegroundColor Cyan
    python -c "from models import init_db; init_db()"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "数据库初始化成功！" -ForegroundColor Green
    }
    else {
        Write-Host "数据库初始化失败！" -ForegroundColor Red
    }
}

# 运行应用（开发模式）
function Run-Dev {
    Write-Host "启动开发服务器..." -ForegroundColor Cyan
    $env:FLASK_ENV = "development"
    python app.py
}

# 运行应用（生产模式）
function Run-Production {
    Write-Host "启动生产服务器..." -ForegroundColor Cyan
    python app.py
}

# Docker 构建
function Docker-Build {
    Write-Host "构建Docker镜像..." -ForegroundColor Cyan
    docker build -t ai-answer-service .
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker镜像构建成功！" -ForegroundColor Green
    }
    else {
        Write-Host "Docker镜像构建失败！" -ForegroundColor Red
    }
}

# Docker 运行
function Docker-Run {
    Write-Host "运行Docker容器..." -ForegroundColor Cyan
    docker run -d --name ai-answer-service -p 5000:5000 --env-file .env ai-answer-service
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker容器启动成功！" -ForegroundColor Green
    }
    else {
        Write-Host "Docker容器启动失败！" -ForegroundColor Red
    }
}

# Docker Compose 启动
function Docker-Compose-Up {
    Write-Host "启动Docker Compose服务..." -ForegroundColor Cyan
    docker-compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker Compose服务启动成功！" -ForegroundColor Green
    }
    else {
        Write-Host "Docker Compose服务启动失败！" -ForegroundColor Red
    }
}

# Docker Compose 停止
function Docker-Compose-Down {
    Write-Host "停止Docker Compose服务..." -ForegroundColor Cyan
    docker-compose down
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker Compose服务停止成功！" -ForegroundColor Green
    }
    else {
        Write-Host "Docker Compose服务停止失败！" -ForegroundColor Red
    }
}

# 数据库迁移生成
function DB-Migrate {
    Write-Host "生成数据库迁移..." -ForegroundColor Cyan
    alembic revision --autogenerate -m "Auto migration"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "数据库迁移生成成功！" -ForegroundColor Green
    }
    else {
        Write-Host "数据库迁移生成失败！" -ForegroundColor Red
    }
}

# 数据库迁移应用
function DB-Upgrade {
    Write-Host "应用数据库迁移..." -ForegroundColor Cyan
    alembic upgrade head
    if ($LASTEXITCODE -eq 0) {
        Write-Host "数据库迁移应用成功！" -ForegroundColor Green
    }
    else {
        Write-Host "数据库迁移应用失败！" -ForegroundColor Red
    }
}

# 安装pre-commit钩子
function Install-PreCommit {
    Write-Host "安装pre-commit钩子..." -ForegroundColor Cyan
    pre-commit install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "pre-commit钩子安装成功！" -ForegroundColor Green
    }
    else {
        Write-Host "pre-commit钩子安装失败！" -ForegroundColor Red
    }
}

# 运行pre-commit检查
function Run-PreCommit {
    Write-Host "运行pre-commit检查..." -ForegroundColor Cyan
    pre-commit run --all-files
    if ($LASTEXITCODE -eq 0) {
        Write-Host "pre-commit检查通过！" -ForegroundColor Green
    }
    else {
        Write-Host "pre-commit检查失败！" -ForegroundColor Red
    }
}

# 显示帮助信息
function Show-Help {
    Write-Host "EduBrain AI - Windows PowerShell 脚本" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "可用命令:" -ForegroundColor Yellow
    Write-Host "  Install-Production    安装生产依赖" -ForegroundColor White
    Write-Host "  Install-Development   安装开发依赖" -ForegroundColor White
    Write-Host "  Run-Tests            运行测试" -ForegroundColor White
    Write-Host "  Run-Lint             运行代码检查" -ForegroundColor White
    Write-Host "  Run-Format           格式化代码" -ForegroundColor White
    Write-Host "  Clean-Cache          清理缓存文件" -ForegroundColor White
    Write-Host "  Init-Database        初始化数据库" -ForegroundColor White
    Write-Host "  Run-Dev              开发模式运行" -ForegroundColor White
    Write-Host "  Run-Production       生产模式运行" -ForegroundColor White
    Write-Host "  Docker-Build         构建Docker镜像" -ForegroundColor White
    Write-Host "  Docker-Run           运行Docker容器" -ForegroundColor White
    Write-Host "  Docker-Compose-Up    启动Docker Compose" -ForegroundColor White
    Write-Host "  Docker-Compose-Down  停止Docker Compose" -ForegroundColor White
    Write-Host "  DB-Migrate           生成数据库迁移" -ForegroundColor White
    Write-Host "  DB-Upgrade           应用数据库迁移" -ForegroundColor White
    Write-Host "  Install-PreCommit    安装pre-commit钩子" -ForegroundColor White
    Write-Host "  Run-PreCommit        运行pre-commit检查" -ForegroundColor White
    Write-Host "  Show-Help            显示此帮助信息" -ForegroundColor White
    Write-Host ""
    Write-Host "使用示例:" -ForegroundColor Yellow
    Write-Host "  .\build.ps1 Install-Development" -ForegroundColor White
    Write-Host "  .\build.ps1 Run-Tests" -ForegroundColor White
    Write-Host ""
}

# 主函数
function Main {
    param([string]$Command)

    switch ($Command) {
        "install" { Install-Production }
        "dev-install" { Install-Development }
        "test" { Run-Tests }
        "lint" { Run-Lint }
        "format" { Run-Format }
        "clean" { Clean-Cache }
        "db-init" { Init-Database }
        "run-dev" { Run-Dev }
        "run" { Run-Production }
        "docker-build" { Docker-Build }
        "docker-run" { Docker-Run }
        "docker-compose-up" { Docker-Compose-Up }
        "docker-compose-down" { Docker-Compose-Down }
        "db-migrate" { DB-Migrate }
        "db-upgrade" { DB-Upgrade }
        "pre-commit-install" { Install-PreCommit }
        "pre-commit-run" { Run-PreCommit }
        "help" { Show-Help }
        default {
            Write-Host "未知命令: $Command" -ForegroundColor Red
            Write-Host "运行 '.\build.ps1 help' 查看可用命令" -ForegroundColor Yellow
        }
    }
}

# 如果直接运行脚本，显示帮助
if ($MyInvocation.InvocationName -eq $MyInvocation.MyCommand.Name) {
    if ($args.Count -eq 0) {
        Show-Help
    }
    else {
        Main $args[0]
    }
}
