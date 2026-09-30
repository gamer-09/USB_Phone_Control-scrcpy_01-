$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$platformTools = Join-Path $projectDir "tools\platform-tools"
$adb = Join-Path $platformTools "adb.exe"
if (!(Test-Path -LiteralPath $adb)) {
  throw "adb.exe not found. Run scripts\setup.ps1 first."
}

$scrcpyRoot = Join-Path $projectDir "tools\scrcpy"
$scrcpyExe = Get-ChildItem -LiteralPath $scrcpyRoot -Recurse -Filter "scrcpy.exe" | Select-Object -First 1
if ($null -eq $scrcpyExe) {
  throw "scrcpy.exe not found. Run scripts\setup.ps1 first."
}

$env:PATH = "$platformTools;$env:PATH"

Write-Host "\nAndroid Wireless Debugging (ADB over Wi-Fi)\n" -ForegroundColor Cyan
Write-Host "On your phone: Developer options > Wireless debugging\n" -ForegroundColor Cyan

$pairHostPort = Read-Host "Pair IP:port (example: 192.168.1.23:37099) (from 'Pair device with pairing code')"
$pairCode = Read-Host "Pairing code (6 digits)"
$connectHostPort = Read-Host "Connect IP:port (example: 192.168.1.23:42593) (from Wireless debugging main screen)"

if ([string]::IsNullOrWhiteSpace($pairHostPort) -or [string]::IsNullOrWhiteSpace($pairCode) -or [string]::IsNullOrWhiteSpace($connectHostPort)) {
  throw "All fields are required."
}

if ($pairHostPort -match '^\d+$' -or $connectHostPort -match '^\d+$') {
  throw "Enter the full IP:port (not just the port). Example: 192.168.1.23:42593"
}

if ($pairHostPort -notmatch '^[0-9\.]+:\d+$' -or $connectHostPort -notmatch '^[0-9\.]+:\d+$') {
  throw "Invalid format. Use IP:port (example: 192.168.1.23:42593)"
}

& $adb kill-server | Out-Null
& $adb start-server | Out-Null

Write-Host "\nPairing..." -ForegroundColor Yellow
& $adb pair $pairHostPort $pairCode

Write-Host "\nConnecting..." -ForegroundColor Yellow
& $adb connect $connectHostPort

Write-Host "\nDevices:" -ForegroundColor Yellow
& $adb devices -l

Write-Host "\nStarting scrcpy over Wi-Fi..." -ForegroundColor Green
& $scrcpyExe.FullName -s $connectHostPort
