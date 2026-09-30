$ErrorActionPreference = "Stop"

$scriptDir = if ($null -ne $PSScriptRoot -and $PSScriptRoot -ne "") { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$root = Split-Path -Parent $scriptDir
if ($null -eq $root -or $root -eq "") {
  throw "Could not determine project root directory."
}
$toolsDir = Join-Path $root "tools"
$downloadsDir = Join-Path $toolsDir "downloads"

New-Item -ItemType Directory -Force -Path $downloadsDir | Out-Null

function Invoke-FileDownload {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$DestinationPath
  )

  # WebClient treats paths literally (safe inside folders with brackets such as
  # "USB Phone Control [scrcpy_01]"), unlike Invoke-WebRequest -OutFile which
  # resolves wildcards. DownloadFileTaskAsync lets us enforce a timeout so
  # stalled downloads fail instead of hanging forever.
  $wc = New-Object System.Net.WebClient
  try {
    $task = $wc.DownloadFileTaskAsync($Url, $DestinationPath)
    if (-not $task.Wait([TimeSpan]::FromSeconds(600))) {
      $wc.CancelAsync()
      throw "Download timed out after 10 minutes: $Url"
    }
  } finally {
    $wc.Dispose()
  }
}

$platformToolsZip = Join-Path $downloadsDir "platform-tools-latest-windows.zip"
$platformToolsUrl = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"

$scrcpyVersion = "4.1"
$scrcpyZipName = "scrcpy-win64-v$scrcpyVersion.zip"
$scrcpyZip = Join-Path $downloadsDir $scrcpyZipName
$scrcpyUrl = "https://github.com/Genymobile/scrcpy/releases/download/v$scrcpyVersion/$scrcpyZipName"

Write-Host "Downloading Android platform-tools (ADB)..."
Invoke-FileDownload -Url $platformToolsUrl -DestinationPath $platformToolsZip

Write-Host "Downloading scrcpy v$scrcpyVersion..."
Invoke-FileDownload -Url $scrcpyUrl -DestinationPath $scrcpyZip

$platformToolsDir = Join-Path $toolsDir "platform-tools"
if (Test-Path -LiteralPath $platformToolsDir) { Remove-Item -LiteralPath $platformToolsDir -Recurse -Force }

$scrcpyDir = Join-Path $toolsDir "scrcpy"
if (Test-Path -LiteralPath $scrcpyDir) { Remove-Item -LiteralPath $scrcpyDir -Recurse -Force }

New-Item -ItemType Directory -Force -Path $scrcpyDir | Out-Null

Add-Type -AssemblyName System.IO.Compression.FileSystem

Write-Host "Extracting platform-tools..."
[System.IO.Compression.ZipFile]::ExtractToDirectory($platformToolsZip, $toolsDir)

Write-Host "Extracting scrcpy..."
[System.IO.Compression.ZipFile]::ExtractToDirectory($scrcpyZip, $scrcpyDir)

Write-Host "Done. Next: connect your phone, enable USB debugging, then run .\\scripts\\check-device.ps1 and .\\scripts\\run.ps1"
