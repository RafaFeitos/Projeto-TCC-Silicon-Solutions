$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"

Write-Host ""
Write-Host "========================================"
Write-Host " Industrial Monitor - Backend"
Write-Host "========================================"
Write-Host ""

Set-Location $BackendDir

Write-Host "Iniciando FastAPI em http://localhost:8000"
Write-Host "Documentacao: http://localhost:8000/docs"
Write-Host ""

python -m uvicorn app.main:app --reload --host 127.0.0.1  --port 8000