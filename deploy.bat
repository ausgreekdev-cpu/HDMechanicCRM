@echo off
REM HDMechanicCRM - Production Deploy Script
REM Run this on your server to deploy

echo ========================================
echo  HDMechanicCRM Production Deploy
echo ========================================

REM Check for Docker
docker --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Docker is not installed
    echo Install from: https://docs.docker.com/get-docker/
    pause
    exit /b 1
)

docker compose version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    docker-compose --version >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Docker Compose is not installed
        pause
        exit /b 1
    )
)

REM Check for .env
if not exist ".env" (
    echo.
    echo No .env file found. Creating from template...
    copy .env.example .env >nul
    echo.
    echo IMPORTANT: Edit .env and set these values:
    echo   CRM_SECRET_KEY - Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    echo   CRM_ADMIN_PASSWORD - Your admin password
    echo.
    notepad .env
    pause
    exit /b 1
)

REM Generate secret key if still default
findstr /C:"change-me-to-a-random-64-char-string" .env >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo.
    echo WARNING: CRM_SECRET_KEY is still the default value!
    echo Generate a real key and update .env before deploying.
    echo.
    pause
)

echo.
echo [1/4] Building Docker image...
docker compose build

echo.
echo [2/4] Stopping existing containers...
docker compose down

echo.
echo [3/4] Starting services...
docker compose up -d

echo.
echo [4/4] Waiting for health check...
timeout /t 10 /nobreak >nul

docker compose ps
echo.
echo ========================================
echo  Deploy Complete!
echo ========================================
echo.
echo  App:    http://localhost
echo  Health: http://localhost/health
echo  Logs:   docker compose logs -f web
echo  Stop:   docker compose down
echo ========================================

pause
