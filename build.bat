@echo off
REM EduBrain AI - Windows Batch Script
REM Alternative to Makefile functionality

REM Set Python executable path
set PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="install" goto install
if "%1"=="dev-install" goto dev-install
if "%1"=="test" goto test
if "%1"=="lint" goto lint
if "%1"=="format" goto format
if "%1"=="clean" goto clean
if "%1"=="db-init" goto db-init
if "%1"=="run-dev" goto run-dev
if "%1"=="run" goto run
if "%1"=="docker-build" goto docker-build
if "%1"=="docker-run" goto docker-run
if "%1"=="docker-compose-up" goto docker-compose-up
if "%1"=="docker-compose-down" goto docker-compose-down
if "%1"=="db-migrate" goto db-migrate
if "%1"=="db-upgrade" goto db-upgrade
if "%1"=="pre-commit-install" goto pre-commit-install
if "%1"=="pre-commit-run" goto pre-commit-run
goto unknown

:help
echo EduBrain AI - Windows Batch Script
echo ===================================
echo.
echo Available commands:
echo   install              Install production dependencies
echo   dev-install          Install development dependencies
echo   test                 Run tests
echo   lint                 Run code linting
echo   format               Format code
echo   clean                Clean cache files
echo   db-init              Initialize database
echo   run-dev              Run in development mode
echo   run                  Run in production mode
echo   docker-build         Build Docker image
echo   docker-run           Run Docker container
echo   docker-compose-up    Start Docker Compose
echo   docker-compose-down  Stop Docker Compose
echo   db-migrate           Generate database migration
echo   db-upgrade           Apply database migration
echo   pre-commit-install   Install pre-commit hooks
echo   pre-commit-run       Run pre-commit checks
echo   help                 Show this help information
echo.
echo Usage examples:
echo   .\build.bat dev-install
echo   .\build.bat test
echo.
goto end

:install
echo Installing production dependencies...
%PYTHON_EXE% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Production dependencies installation failed!
    goto end
)
echo Production dependencies installed successfully!
goto end

:dev-install
echo Installing development dependencies...
%PYTHON_EXE% -m pip install -r requirements.txt
%PYTHON_EXE% -m pip install black isort flake8 mypy pre-commit pytest pytest-asyncio
if %errorlevel% neq 0 (
    echo Development dependencies installation failed!
    goto end
)
echo Development dependencies installed successfully!
goto end

:test
echo Running tests...
pytest tests/ -v --cov=app --cov=utils --cov-report=html
if %errorlevel% neq 0 (
    echo Tests failed!
    goto end
)
echo Tests completed successfully!
goto end

:lint
echo Running code linting...
flake8 app.py utils.py models.py config.py prompts.py
if %errorlevel% neq 0 (
    echo Code linting failed!
    goto end
)
echo Code linting passed!
goto end

:format
echo Formatting code...
black app.py utils.py models.py config.py prompts.py
isort app.py utils.py models.py config.py prompts.py
if %errorlevel% neq 0 (
    echo Code formatting failed!
    goto end
)
echo Code formatting completed!
goto end

:clean
echo Cleaning cache files...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f"
for /r . %%f in (*.pyo) do @if exist "%%f" del /q "%%f"
for /r . %%f in (*.egg-info) do @if exist "%%f" rd /s /q "%%f"
for /r . %%f in (.coverage) do @if exist "%%f" del /q "%%f"
for /d /r . %%d in (htmlcov) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (.pytest_cache) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (.mypy_cache) do @if exist "%%d" rd /s /q "%%d"
echo Cache cleanup completed!
goto end

:db-init
echo Initializing database...
%PYTHON_EXE% -c "from models import init_db; init_db()"
if %errorlevel% neq 0 (
    echo Database initialization failed!
    goto end
)
echo Database initialized successfully!
goto end

:run-dev
echo Starting development server...
set FLASK_ENV=development
%PYTHON_EXE% app.py
goto end

:run
echo Starting production server...
%PYTHON_EXE% app.py
goto end

:docker-build
echo Building Docker image...
docker build -t ai-answer-service .
if %errorlevel% neq 0 (
    echo Docker image build failed!
    goto end
)
echo Docker image built successfully!
goto end

:docker-run
echo Running Docker container...
docker run -d --name ai-answer-service -p 5000:5000 --env-file .env ai-answer-service
if %errorlevel% neq 0 (
    echo Docker container start failed!
    goto end
)
echo Docker container started successfully!
goto end

:docker-compose-up
echo Starting Docker Compose services...
docker-compose up -d
if %errorlevel% neq 0 (
    echo Docker Compose start failed!
    goto end
)
echo Docker Compose services started successfully!
goto end

:docker-compose-down
echo Stopping Docker Compose services...
docker-compose down
if %errorlevel% neq 0 (
    echo Docker Compose stop failed!
    goto end
)
echo Docker Compose services stopped successfully!
goto end

:db-migrate
echo Generating database migration...
%PYTHON_EXE% -m alembic revision --autogenerate -m "Auto migration"
if %errorlevel% neq 0 (
    echo Database migration generation failed!
    goto end
)
echo Database migration generated successfully!
goto end

:db-upgrade
echo Applying database migration...
%PYTHON_EXE% -m alembic upgrade head
if %errorlevel% neq 0 (
    echo Database migration application failed!
    goto end
)
echo Database migration applied successfully!
goto end

:pre-commit-install
echo Installing pre-commit hooks...
%PYTHON_EXE% -m pre_commit install
if %errorlevel% neq 0 (
    echo Pre-commit hooks installation failed!
    goto end
)
echo Pre-commit hooks installed successfully!
goto end

:pre-commit-run
echo Running pre-commit checks...
%PYTHON_EXE% -m pre_commit run --all-files
if %errorlevel% neq 0 (
    echo Pre-commit checks failed!
    goto end
)
echo Pre-commit checks passed!
goto end

:unknown
echo Unknown command: %1
echo Run '.\build.bat help' to see available commands
goto end

:end
