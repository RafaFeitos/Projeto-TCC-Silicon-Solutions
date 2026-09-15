@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
set "BACKEND_DIR=%PROJECT_ROOT%\backend"

echo.
echo ========================================
echo  Industrial Monitor - Backend
echo ========================================
echo.

cd /d "%BACKEND_DIR%"

echo Iniciando FastAPI em http://localhost:8000
echo Documentacao: http://localhost:8000/docs
echo.

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

endlocal