$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DashboardDir = Join-Path $ProjectRoot "dashboard"

Write-Host ""
Write-Host "========================================"
Write-Host " Industrial Monitor - Dashboard"
Write-Host "========================================"
Write-Host ""

Set-Location $DashboardDir

Write-Host "Iniciando Next.js em http://localhost:3000"
Write-Host ""

npm run dev