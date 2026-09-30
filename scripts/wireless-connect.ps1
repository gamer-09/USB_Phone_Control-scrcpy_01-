param(
  [Parameter(Mandatory = $true)][string]$HostPort
)

$ErrorActionPreference = "Stop"

$scriptDir = if ($null -ne $PSScriptRoot -and $PSScriptRoot -ne "") { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$root = Split-Path -Parent $scriptDir
if ($null -eq $root -or $root -eq "") { throw "Could not determine project root directory." }

$platformTools = Join-Path $root "tools\platform-tools"
$adb = Join-Path $platformTools "adb.exe"
if (!(Test-Path -LiteralPath $adb)) { throw "adb.exe not found. Run .\\scripts\\setup.ps1 first." }

$env:PATH = "$platformTools;$env:PATH"

& $adb connect $HostPort
