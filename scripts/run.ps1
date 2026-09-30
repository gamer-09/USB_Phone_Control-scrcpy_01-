param(
  [Parameter(Mandatory = $false)][string]$Serial,
  [Parameter(Mandatory = $false)][switch]$NoAudio,
  [Parameter(Mandatory = $false)][string]$AudioSource = "output",
  [Parameter(Mandatory = $false)][string]$AudioBitRate = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = if ($null -ne $PSScriptRoot -and $PSScriptRoot -ne "") { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$root = Split-Path -Parent $scriptDir
if ($null -eq $root -or $root -eq "") {
  throw "Could not determine project root directory."
}
$platformTools = Join-Path $root "tools\platform-tools"
$adb = Join-Path $platformTools "adb.exe"
if (!(Test-Path -LiteralPath $adb)) {
  throw "adb.exe not found. Run .\\scripts\\setup.ps1 first."
}

$scrcpyRoot = Join-Path $root "tools\scrcpy"
$scrcpyExe = Get-ChildItem -LiteralPath $scrcpyRoot -Recurse -Filter "scrcpy.exe" | Select-Object -First 1
if ($null -eq $scrcpyExe) {
  throw "scrcpy.exe not found. Run .\\scripts\\setup.ps1 first."
}

$env:PATH = "$platformTools;$env:PATH"
$env:ADB = $adb

$scrcpyArgs = @()
if ($Serial -and $Serial.Trim() -ne "") {
  $scrcpyArgs += "-s"
  $scrcpyArgs += $Serial.Trim()
  # Wireless: apply more conservative defaults to reduce lag
  $scrcpyArgs += "--max-size"
  $scrcpyArgs += "1024"
  $scrcpyArgs += "--video-bit-rate"
  $scrcpyArgs += "2M"
  $scrcpyArgs += "--max-fps"
  $scrcpyArgs += "30"
}

# Audio is forwarded by default (video + audio, like a camera feed).
# -NoAudio disables it entirely; -AudioSource selects what is captured
# (audio is then played on the PC by default):
#   output (default)               -> the phone's own audio output
#   playback                       -> the phone's audio playback (apps can opt out)
#   mic                            -> the phone's microphone (acts as a remote mic for the PC)
#   mic-voice-communication        -> mic tuned for calls (echo cancellation)
#   voice-performance              -> both the microphone and the device playback
#   ... (see scrcpy --help for all sources)
if ($NoAudio) {
  $scrcpyArgs += "--no-audio"
}
else {
  $audioSource = $AudioSource.Trim().ToLower()
  if ($audioSource -eq "") { $audioSource = "output" }
  $validSources = @("output", "playback", "mic", "mic-unprocessed", "mic-camcorder", "mic-voice-recognition", "mic-voice-communication", "voice-call", "voice-call-uplink", "voice-call-downlink", "voice-performance")
  if ($validSources -notcontains $audioSource) {
    throw "Invalid -AudioSource '$audioSource'. Valid values: $($validSources -join ', ')"
  }
  $scrcpyArgs += "--audio-source"
  $scrcpyArgs += $audioSource
  if ($AudioBitRate.Trim() -ne "") {
    $scrcpyArgs += "--audio-bit-rate"
    $scrcpyArgs += $AudioBitRate.Trim()
  }
}

& $scrcpyExe.FullName @scrcpyArgs
