# EduBrain AI - 智能题库系统

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<div align="center">
  <img src="https://img.shields.io/badge/版本-2.3.1-brightgreen" alt="Version"/>
  <img src="https://img.shields.io/badge/状态-稳定运行-success" alt="Status"/>
  <img src="https://img.shields.io/badge/界面-现代化-blue" alt="UI"/>
</div>

## 📖 项目简介

EduBrain AI 是一个基于 Python 和大型语言模型的全新智能题库服务，专为 [OCS (Online Course Script)](https://github.com/ocsjs/ocsjs) 设计。它实现了与 OCS AnswererWrapper 兼容的 API 接口，方便用户将 AI 能力整合到 OCS 题库搜索中。

### ✨ 核心特性

-   🤖 **多 AI 引擎驱动**：支持 OpenAI API 和 Google Gemini API，可灵活切换
-   🔄 **OCS 完美兼容**：完全兼容 OCS 的 AnswererWrapper 题库接口
-   🏆 **外部题库优先查询**：支持言溪题库、GO 题库等，AI 作为备选方案
-   🚀 **高性能架构**：异步处理 + Redis 缓存 + 数据库优化
-   🔒 **企业级安全**：访问令牌验证 + 非 root 容器运行（可选）
-   💬 **智能题型识别**：支持单选、多选、判断、填空、阅读理解等题型
-   📊 **实时监控**：完整的统计信息和健康检查
-   🌐 **现代化界面**：响应式 Web 界面，支持多设备访问
-   🪟 **Windows 完美支持**：提供 PowerShell 和批处理脚本，无需 make 工具

### 🎨 界面预览

-   **首页**：现代化的渐变设计，智能表单验证，实时反馈
-   **统计面板**：精美的统计卡片，数据可视化，交互式表格
-   **API 文档**：标签页布局，代码示例，详细配置指南

### 🏗️ 架构优势

-   **异步处理**：支持高并发请求，显著提升响应速度
-   **智能缓存**：Redis 缓存 + 内存缓存双重保障
-   **外部集成**：优先查询外部题库，降低 AI 成本
-   **模块化设计**：代码结构清晰，便于维护和扩展
-   **配置灵活**：环境变量配置，支持个性化定制

## ⚠️ 重要提示

> [!IMPORTANT]
>
> -   本项目仅供个人学习使用，不保证稳定性，且不提供任何技术支持。
> -   使用者必须在遵循所选 AI 提供商（OpenAI 或 Google Gemini）的**使用条款**以及**相关法律法规**的情况下使用，不得用于非法用途。
>     -   OpenAI 使用条款: [OpenAI Policies](https://openai.com/policies)
>     -   Google AI 使用条款: [Google AI Terms of Service](https://policies.google.com/terms)
> -   根据[《生成式人工智能服务管理暂行办法》](http://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm)的要求，请勿对中国地区公众提供一切未经备案的生成式人工智能服务。
> -   使用者应当遵守相关法律法规，承担相应的法律责任
> -   服务不对 AI 生成内容的准确性做出保证

## 📋 系统要求

-   **Python**: 3.9+
-   **内存**: 建议 2GB 以上
-   **存储**: 建议 1GB 以上可用空间
-   **网络**: 能够访问 OpenAI 或 Gemini API
-   **API 密钥**: OpenAI API Key 或 Google Gemini API Key

## 🏃‍♂️ 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/Ivelisya/ocsjs-ai-answer-service.git
cd ocsjs-ai-answer-service

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 2. 安装依赖

```bash
# 生产环境
pip install -r requirements.txt

# 开发环境（包含测试和代码质量工具）
pip install -r requirements.txt
pip install black isort flake8 mypy pre-commit pytest pytest-asyncio

# Windows 用户可以使用脚本
# PowerShell: .\build.ps1 dev-install
# 批处理: .\build.bat dev-install
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env  # 或使用其他编辑器
```

**核心配置说明：**

```env
# AI 提供商配置
AI_PROVIDER=gemini  # 或 openai

# OpenAI 配置（当 AI_PROVIDER=openai 时）
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# Gemini 配置（当 AI_PROVIDER=gemini 时）
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# 服务配置
HOST=0.0.0.0
PORT=5000
DEBUG=false

# 安全配置
ACCESS_TOKEN=your_secret_token_here

# 缓存配置
ENABLE_CACHE=true
REDIS_URL=redis://localhost:6379/0

# 数据库配置
DATABASE_URL=sqlite:///db/dev.db
```

**新增外部题库配置：**

```env
# 外部题库配置（可选，默认启用）
ENABLE_EXTERNAL_DATABASE=True           # 是否启用外部题库查询
EXTERNAL_DATABASE_TIMEOUT=10            # 查询超时时间（秒）

# 安全功能配置（可选，默认禁用，适合个人使用）
ENABLE_RATE_LIMIT=False                 # 是否启用速率限制
ENABLE_INPUT_VALIDATION=False           # 是否启用输入验证
```

### 4. 配置外部题库（可选）

创建 `external_databases.json` 文件来自定义外部题库配置：

```json
{
    "enabled": true,
    "timeout": 10,
    "databases": [
        {
            "name": "言溪题库",
            "url": "https://tk.enncy.cn/query",
            "method": "get",
            "data": {
                "token": "your_token_here",
                "title": "${title}",
                "options": "${options}",
                "type": "${type}"
            },
            "enabled": true
        }
    ]
}
```

### 5. 初始化数据库

```bash
# 初始化数据库
python -c "from models import init_db; init_db()"

# 或使用脚本
# Linux/Mac: make db-init
# Windows PowerShell: .\build.ps1 db-init
# Windows 批处理: .\build.bat db-init
```

### 6. 启动服务

```bash
# 开发模式
python app.py

# 或使用Docker
docker-compose up -d

# Windows 用户
# PowerShell: .\build.ps1 run-dev
# 批处理: .\build.bat run-dev
# Docker: .\build.ps1 docker-compose-up 或 .\build.bat docker-compose-up
```

#### Windows Python 环境设置

如果遇到 `python` 命令无法识别的问题，请使用以下方法之一：

**方法 1：使用启动脚本（推荐）**

```bash
python start.py
```

**方法 2：临时设置环境变量**

```powershell
# 在PowerShell中临时设置
$env:Path = "C:\Users\20212\AppData\Local\Programs\Python\Python310;" + $env:Path
python app.py
```

**方法 3：永久设置环境变量**

1. 右键"此电脑" → "属性" → "高级系统设置"
2. 点击"环境变量"
3. 在"系统变量"中找到"Path"，点击"编辑"
4. 添加 `C:\Users\20212\AppData\Local\Programs\Python\Python310\` 到路径中

#### PowerShell 脚本执行设置

如果遇到 PowerShell 脚本无法执行的问题：

```batch
# 运行设置工具（推荐）
.\setup_powershell.bat
```

或手动设置：

```powershell
# 以管理员身份运行 PowerShell，执行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

服务启动后访问：<http://localhost:5000>

## 🪟 Windows 快速开始指南

### 环境准备

#### 1. 安装 Python

访问 [Python 官网](https://www.python.org/downloads/) 下载并安装 Python 3.9+。

安装时请勾选：

-   [x] Add Python to PATH
-   [x] Install pip

#### 2. 验证安装

```powershell
# 打开 PowerShell，验证 Python 版本
python --version
pip --version
```

#### 3. 克隆项目

```powershell
# 克隆项目到本地
git clone https://github.com/Ivelisya/ocsjs-ai-answer-service.git
cd ocsjs-ai-answer-service
```

### 使用 PowerShell 脚本（推荐）

#### 1. 设置执行策略

```powershell
# 允许执行脚本（管理员权限）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 2. 安装依赖

```powershell
# 安装生产环境依赖
.\build.ps1 install

# 或安装开发环境依赖（包含测试工具）
.\build.ps1 dev-install
```

#### 3. 配置环境变量

```powershell
# 复制环境变量模板
Copy-Item .env.example .env

# 编辑配置文件
notepad .env
```

#### 4. 初始化数据库

```powershell
# 初始化数据库
.\build.ps1 db-init
```

#### 5. 启动服务

```powershell
# 开发模式启动
.\build.ps1 run-dev

# 或生产模式启动
.\build.ps1 run
```

### 使用批处理脚本（兼容性更好）

#### 1. 安装依赖

```batch
# 安装生产环境依赖
.\build.bat install

# 或安装开发环境依赖
.\build.bat dev-install
```

#### 2. 配置环境变量

```batch
# 复制环境变量模板
copy .env.example .env

# 编辑配置文件
notepad .env
```

#### 3. 初始化数据库

```batch
# 初始化数据库
.\build.bat db-init
```

#### 4. 启动服务

```batch
# 开发模式启动
.\build.bat run-dev

# 或生产模式启动
.\build.bat run
```

### Docker 部署（Windows）

#### 使用 Docker Desktop

1. 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. 启动 Docker Desktop

#### 使用 PowerShell 脚本

```powershell
# 构建镜像
.\build.ps1 docker-build

# 运行容器
.\build.ps1 docker-run

# 或使用 Docker Compose
.\build.ps1 docker-compose-up
```

#### 使用批处理脚本

```batch
# 构建镜像
.\build.bat docker-build

# 运行容器
.\build.bat docker-run

# 或使用 Docker Compose
.\build.bat docker-compose-up
```

### 常见 Windows 问题解决

#### 1. PowerShell 执行策略错误

```powershell
# 以管理员身份运行 PowerShell，执行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine

# 或仅为当前用户设置
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 2. Python 命令无法识别

重新安装 Python 时，确保勾选 "Add Python to PATH"。

#### 3. 端口占用问题

```powershell
# 查看端口占用
netstat -ano | findstr :5000

# 杀死进程（将 PID 替换为实际进程 ID）
taskkill /PID <PID> /F
```

#### 4. 权限问题

```powershell
# 以管理员身份运行 PowerShell
# 右键 PowerShell -> "以管理员身份运行"
```

#### 5. 虚拟环境激活失败

```powershell
# 确保虚拟环境存在
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\activate
```

#### 6. 依赖安装失败

```powershell
# 升级 pip
python -m pip install --upgrade pip

# 使用国内源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 脚本功能列表

| 脚本                | 功能                 | PowerShell                        | 批处理                            |
| ------------------- | -------------------- | --------------------------------- | --------------------------------- |
| install             | 安装生产依赖         | `.\build.ps1 install`             | `.\build.bat install`             |
| dev-install         | 安装开发依赖         | `.\build.ps1 dev-install`         | `.\build.bat dev-install`         |
| test                | 运行测试             | `.\build.ps1 test`                | `.\build.bat test`                |
| lint                | 代码检查             | `.\build.ps1 lint`                | `.\build.bat lint`                |
| format              | 代码格式化           | `.\build.ps1 format`              | `.\build.bat format`              |
| clean               | 清理缓存             | `.\build.ps1 clean`               | `.\build.bat clean`               |
| db-init             | 初始化数据库         | `.\build.ps1 db-init`             | `.\build.bat db-init`             |
| run-dev             | 开发模式运行         | `.\build.ps1 run-dev`             | `.\build.bat run-dev`             |
| run                 | 生产模式运行         | `.\build.ps1 run`                 | `.\build.bat run`                 |
| docker-build        | 构建 Docker 镜像     | `.\build.ps1 docker-build`        | `.\build.bat docker-build`        |
| docker-run          | 运行 Docker 容器     | `.\build.ps1 docker-run`          | `.\build.bat docker-run`          |
| docker-compose-up   | 启动 Docker Compose  | `.\build.ps1 docker-compose-up`   | `.\build.bat docker-compose-up`   |
| docker-compose-down | 停止 Docker Compose  | `.\build.ps1 docker-compose-down` | `.\build.bat docker-compose-down` |
| db-migrate          | 生成数据库迁移       | `.\build.ps1 db-migrate`          | `.\build.bat db-migrate`          |
| db-upgrade          | 应用数据库迁移       | `.\build.ps1 db-upgrade`          | `.\build.bat db-upgrade`          |
| pre-commit-install  | 安装 pre-commit 钩子 | `.\build.ps1 pre-commit-install`  | `.\build.bat pre-commit-install`  |
| pre-commit-run      | 运行 pre-commit 检查 | `.\build.ps1 pre-commit-run`      | `.\build.bat pre-commit-run`      |
| help                | 显示帮助信息         | `.\build.ps1 help`                | `.\build.bat help`                |

## 🔧 开发指南

### Linux/Mac 用户（使用 Makefile）

```bash
# 安装pre-commit钩子
make pre-commit-install

# 运行所有检查
make pre-commit-run

# 单独运行
make lint      # 代码检查
make format    # 代码格式化
make test      # 运行测试
```

### 代码质量保证

#### 自动化工具配置

项目使用了以下代码质量工具：

-   **Black**: 代码自动格式化
-   **isort**: 导入语句排序
-   **Flake8**: 代码风格检查
-   **MyPy**: 静态类型检查
-   **Pre-commit**: Git 钩子自动化检查

#### 安装和配置

```bash
# Linux/Mac
make pre-commit-install

# Windows
.\build.ps1 pre-commit-install
```

### 测试执行

#### 完整测试套件

```bash
# Linux/Mac
make test

# Windows
.\build.ps1 test

# 带覆盖率报告
pytest tests/ -v --cov=app --cov-report=html

# 运行特定测试
pytest tests/test_app.py::TestAPI::test_health_endpoint -v
```

### 数据库迁移

#### Alembic 数据库版本管理

```bash
# Linux/Mac
make db-migrate  # 生成迁移文件
make db-upgrade  # 应用迁移

# Windows
.\build.ps1 db-migrate
.\build.ps1 db-upgrade

# 查看迁移历史
alembic history
```

## 📡 API 接口文档

### 核心接口

#### 搜索接口

```http
GET/POST /api/search
```

**请求参数：**

| 参数    | 类型   | 必填 | 说明                                       |
| ------- | ------ | ---- | ------------------------------------------ |
| title   | string | 是   | 题目内容                                   |
| type    | string | 否   | 题型：single/multiple/judgement/completion |
| options | string | 否   | 选项内容                                   |
| context | string | 否   | 上下文信息                                 |

**成功响应：**

```json
{
    "code": 1,
    "question": "中国的首都是哪里？",
    "answer": "北京"
}
```

**错误响应：**

```json
{
    "code": 0,
    "msg": "错误信息"
}
```

#### API 健康检查

```http
GET /api/health
```

**响应：**

```json
{
    "status": "ok",
    "version": "2.3.0",
    "ai_provider": "gemini",
    "model": "gemini-1.5-flash",
    "cache_enabled": true
}
```

#### 统计信息

```http
GET /api/stats
```

**响应：**

```json
{
    "version": "2.3.0",
    "uptime": 3600.5,
    "qa_records_count": 1250,
    "cache_size": 45,
    "ai_provider": "gemini"
}
```

#### 缓存管理

```http
POST /api/cache/clear
```

**请求头：**

```
X-Access-Token: your_token_here
```

**响应：**

```json
{
    "code": 1,
    "message": "缓存已清空"
}
```

### OCS 配置

在 OCS 的题库配置中添加：

```json
[
    {
        "name": "EduBrain AI题库",
        "url": "http://localhost:5000/api/search",
        "method": "get",
        "contentType": "json",
        "data": {
            "title": "${title}",
            "type": "${type}",
            "options": "${options}",
            "context": "${context}"
        },
        "handler": "return (res)=> res.code === 1 ? [res.question, res.answer] : [res.msg, undefined]"
    }
]
```

### 外部题库配置

#### 支持的外部题库

目前支持以下外部题库：

1. **言溪题库** (`https://tk.enncy.cn/query`)
2. **GO 题库** (`https://cx.icodef.com/wyn-nb`)
3. **其他自定义题库**

#### 配置方法

创建 `external_databases.json` 配置文件：

```json
{
    "enabled": true,
    "timeout": 10,
    "databases": [
        {
            "name": "言溪题库",
            "url": "https://tk.enncy.cn/query",
            "method": "get",
            "data": {
                "token": "your_token_here",
                "title": "${title}",
                "options": "${options}",
                "type": "${type}"
            },
            "enabled": true
        },
        {
            "name": "GO题库",
            "url": "https://cx.icodef.com/wyn-nb",
            "method": "post",
            "data": {
                "course": "${course}",
                "question": "${title}",
                "type": "${type}",
                "options": "${options}"
            },
            "enabled": true
        }
    ]
}
```

#### 配置参数说明

| 参数      | 类型    | 必填 | 说明                           |
| --------- | ------- | ---- | ------------------------------ |
| enabled   | boolean | 是   | 是否启用外部题库查询           |
| timeout   | number  | 否   | 查询超时时间（秒），默认 10 秒 |
| databases | array   | 是   | 题库配置数组                   |

#### 题库配置参数

| 参数    | 类型    | 必填 | 说明               |
| ------- | ------- | ---- | ------------------ |
| name    | string  | 是   | 题库名称           |
| url     | string  | 是   | 题库 API 地址      |
| method  | string  | 是   | 请求方法：get/post |
| data    | object  | 是   | 请求数据模板       |
| enabled | boolean | 是   | 是否启用此题库     |

#### 模板变量

在配置中使用以下模板变量：

-   `${title}`: 题目内容
-   `${type}`: 题型
-   `${options}`: 选项内容
-   `${context}`: 上下文信息
-   `${course}`: 课程名称（如果适用）

#### 使用示例

```json
{
    "enabled": true,
    "timeout": 15,
    "databases": [
        {
            "name": "自定义题库",
            "url": "https://api.example.com/search",
            "method": "post",
            "data": {
                "api_key": "your_api_key",
                "question": "${title}",
                "answer_type": "${type}",
                "choices": "${options}"
            },
            "enabled": true
        }
    ]
}
```

#### 工作原理

1. 当收到搜索请求时，首先查询外部题库
2. 如果外部题库返回有效答案，直接返回
3. 如果外部题库查询失败或无结果，自动切换到 AI 查询
4. 支持多个外部题库的并行查询，提高成功率

## 🐳 Docker 部署

### 使用 Docker Compose（推荐）

```bash
# 构建并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# Windows 用户
# PowerShell: .\build.ps1 docker-compose-up
# 批处理: .\build.bat docker-compose-up
```

### 手动 Docker 部署

```bash
# 构建镜像
docker build -t ai-answer-service .

# 运行容器
docker run -d \
  --name ai-answer-service \
  -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/db:/app/db \
  -v $(pwd)/logs:/app/logs \
  ai-answer-service

# Windows 用户
# PowerShell: .\build.ps1 docker-build && .\build.ps1 docker-run
# 批处理: .\build.bat docker-build && .\build.bat docker-run
```

## 🔒 安全配置

### 访问令牌

```env
# 在 .env 中设置
ACCESS_TOKEN=your_super_secret_token_here
```

**使用方式：**

```bash
# HTTP头部
curl -H "X-Access-Token: your_token" http://localhost:5000/api/search

# 或URL参数
curl "http://localhost:5000/api/search?token=your_token&title=测试题目"
```

### 可选安全功能

项目提供了可选的安全功能，适合个人使用时可以选择性启用：

#### 速率限制（可选）

```env
# 启用速率限制
ENABLE_RATE_LIMIT=true

# 配置速率限制参数
RATE_LIMIT_REQUESTS=100    # 每小时最大请求数
RATE_LIMIT_WINDOW=3600     # 时间窗口（秒）
```

#### 输入验证（可选）

```env
# 启用输入验证
ENABLE_INPUT_VALIDATION=true

# 配置验证参数
MAX_TITLE_LENGTH=1000      # 题目最大长度
MAX_OPTIONS_LENGTH=2000    # 选项最大长度
MAX_CONTEXT_LENGTH=5000    # 上下文最大长度
```

#### 安全功能状态检查

可以通过 `/api/health` 接口查看安全功能状态：

```json
{
    "status": "ok",
    "version": "2.3.0",
    "security_features": {
        "rate_limit": false,
        "input_validation": false,
        "access_token": true
    }
}
```

### 生产环境建议

1. **使用强密码**：设置复杂的 ACCESS_TOKEN
2. **HTTPS 部署**：使用反向代理（如 Nginx）提供 HTTPS
3. **网络限制**：只开放必要端口
4. **定期更新**：及时更新依赖包和系统补丁
5. **监控日志**：启用日志监控和告警

## 📊 监控和维护

### 健康检查

```bash
# API健康检查
curl http://localhost:5000/api/health

# Docker健康检查
docker ps
docker stats ai-answer-service
```

### 日志查看

```bash
# 查看应用日志
docker-compose logs -f ai-answer-service

# 或直接查看日志文件
tail -f logs/app.log
```

### 性能监控

-   **响应时间**：通过 `/api/stats` 接口监控
-   **缓存命中率**：查看缓存大小和使用情况
-   **数据库性能**：监控查询响应时间
-   **内存使用**：通过 `docker stats` 监控容器资源

## ❓ 常见问题

### AI 答案准确性

AI 生成的答案可能存在以下情况：

-   选项内容与原题不完全匹配
-   判断题答案可能不准确
-   填空题可能给出模糊或错误答案
-   多选题可能遗漏或多选

**建议：**

-   始终与原题选项进行对照
-   保持独立思考和判断
-   有疑问时以人工判断为准
-   将 AI 答案作为参考，而非唯一依据

### 多选题答案格式

对于多选题，系统期望的答案格式是用`#`分隔的选项内容，例如：

```text
中国#世界#地球
```

### API 请求限制

-   **OpenAI**: 不同模型有不同的 RPM 和 TPM 限制
-   **Gemini**: 免费额度有限，超出需付费

**建议：**

-   合理设置缓存过期时间
-   监控 API 使用量
-   准备备用 API 密钥

### 网络连接问题

确保服务器能够访问：

-   `api.openai.com` (OpenAI)
-   `generativelanguage.googleapis.com` (Gemini)

某些地区可能需要配置代理。

### 模型选择建议

| 模型             | 特点               | 适用场景   |
| ---------------- | ------------------ | ---------- |
| gpt-3.5-turbo    | 速度快，成本低     | 日常使用   |
| gpt-4            | 准确率高，理解力强 | 复杂题目   |
| gemini-2.5-flash | 速度快，免费额度多 | 快速回答   |
| gemini-2.5-pro   | 综合性能优秀       | 高质量需求 |

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

### 开发规范

-   遵循 PEP 8 代码风格
-   添加必要的类型注解
-   编写完整的单元测试
-   更新相关文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

-   [OCS 项目](https://github.com/ocsjs/ocsjs) - 优秀的在线课程脚本框架
-   [OpenAI](https://openai.com/) - 强大的 AI 模型提供商
-   [Google](https://ai.google/) - Gemini AI 模型提供商
-   [Flask](https://flask.palletsprojects.com/) - 优秀的 Python Web 框架

---

**⭐ 如果这个项目对你有帮助，请给它一个星标！**
