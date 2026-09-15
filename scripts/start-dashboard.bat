@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
set "DASHBOARD_DIR=%PROJECT_ROOT%\dashboard"

echo.
echo ========================================
echo  Industrial Monitor - Dashboard
echo ========================================
echo.

cd /d "%DASHBOARD_DIR%"

echo Iniciando Next.js em http://localhost:3000
echo.

call npm run dev

endlocal