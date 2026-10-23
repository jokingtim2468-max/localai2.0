# One-command install of Eclipse on Windows:
#   irm https://github.com/jokingtim2468-max/localai2.0/releases/download/eclipse-latest/install.ps1 | iex
$ErrorActionPreference = "Stop"
$url = "https://github.com/jokingtim2468-max/localai2.0/releases/download/eclipse-latest/EclipseSetup.exe"
$exe = Join-Path $env:TEMP "EclipseSetup.exe"
Write-Host "Downloading Eclipse..."
Invoke-WebRequest -Uri $url -OutFile $exe -UseBasicParsing
Write-Host "Installing (Desktop\Eclipse + desktop shortcut, Ollama if missing)..."
Start-Process -FilePath $exe -ArgumentList '/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/TASKS="ollama,tune"' -Wait
Write-Host "Done. Starting Eclipse."
$app = Join-Path ([Environment]::GetFolderPath('Desktop')) "Eclipse\Eclipse.exe"
if (Test-Path $app) { Start-Process $app }
