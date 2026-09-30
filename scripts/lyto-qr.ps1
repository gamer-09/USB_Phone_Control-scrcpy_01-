param(
  [Parameter(Mandatory = $false)][switch]$LytoDebug
)

$ErrorActionPreference = "Stop"

$scriptDir = if ($null -ne $PSScriptRoot -and $PSScriptRoot -ne "") { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$root = Split-Path -Parent $scriptDir
if ($null -eq $root -or $root -eq "") { throw "Could not determine project root directory." }

$platformTools = Join-Path $root "tools\platform-tools"
$adb = Join-Path $platformTools "adb.exe"
if (!(Test-Path -LiteralPath $adb)) { throw "adb.exe not found. Run .\\scripts\\setup.ps1 first." }

# Ensure lyto can find adb by name via PATH
$env:PATH = "$platformTools;$env:PATH"

$py = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $py) { throw "Python launcher 'py' not found. Install Python 3 and ensure 'py' is available." }

Write-Host "Opening QR pairing window..." -ForegroundColor Cyan
Write-Host "On your phone: Developer options > Wireless debugging > Pair device with QR code" -ForegroundColor Cyan
Write-Host "Then scan the QR shown in the new window." -ForegroundColor Cyan

$pyPath = $py.Source
$lytoCmd = "& `"$pyPath`" -3 -m lyto"
if ($LytoDebug) { $lytoCmd += " --debug" }

$psArgs = @(
  "-NoProfile",
  "-ExecutionPolicy","Bypass",
  "-NoExit",
  "-Command", $lytoCmd
)

Start-Process -FilePath "powershell.exe" -ArgumentList $psArgs
