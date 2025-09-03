.PHONY: help install dev-install test lint format clean docker-build docker-run db-init db-migrate

help: ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## 安装生产依赖
	pip install -r requirements.txt

dev-install: ## 安装开发依赖
	pip install -r requirements.txt
	pip install black isort flake8 mypy pre-commit pytest pytest-asyncio

test: ## 运行测试
	pytest tests/ -v --cov=app --cov=utils --cov-report=html

lint: ## 运行代码检查
	flake8 app.py utils.py models.py config.py prompts.py
	mypy app.py utils.py models.py config.py prompts.py

format: ## 格式化代码
	black app.py utils.py models.py config.py prompts.py
	isort app.py utils.py models.py config.py prompts.py

clean: ## 清理缓存文件
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov .pytest_cache .mypy_cache

docker-build: ## 构建Docker镜像
	docker build -t ai-answer-service .

docker-run: ## 运行Docker容器
	docker run -p 5000:5000 --env-file .env ai-answer-service

docker-compose-up: ## 启动docker-compose服务
	docker-compose up -d

docker-compose-down: ## 停止docker-compose服务
	docker-compose down

db-init: ## 初始化数据库
	python -c "from models import init_db; init_db()"

db-migrate: ## 生成数据库迁移
	alembic revision --autogenerate -m "Auto migration"

db-upgrade: ## 升级数据库
	alembic upgrade head

run: ## 运行应用
	python app.py

run-dev: ## 开发模式运行应用
	export FLASK_ENV=development && python app.py

pre-commit-install: ## 安装pre-commit钩子
	pre-commit install

pre-commit-run: ## 运行pre-commit检查
	pre-commit run --all-files
