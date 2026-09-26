#!/usr/bin/env pwsh
# SnapAI Edge - Start All Services
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SnapAI Edge - Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "`n[1/3] Checking .env file..." -ForegroundColor Yellow
if (-not (Test-Path (Join-Path $root ".env"))) {
    Copy-Item (Join-Path $root ".env.example") (Join-Path $root ".env")
    Write-Host "  Created .env from .env.example. Please add your API keys." -ForegroundColor Red
}

Write-Host "`n[2/3] Starting Backend (FastAPI)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backend'; python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload" -WindowStyle Normal

Start-Sleep 3

Write-Host "`n[3/3] Starting Frontend (Vite)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "cd '$frontend'; npm.cmd run dev" -WindowStyle Normal

Start-Sleep 2

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  SnapAI Edge is starting!" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green

Start-Sleep 2
Start-Process "http://localhost:5173"
