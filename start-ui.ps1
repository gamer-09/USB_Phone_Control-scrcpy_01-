$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$py = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $py) {
  & py -3 (Join-Path $projectDir "phone_control_ui.py")
  exit
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -ne $python) {
  & python (Join-Path $projectDir "phone_control_ui.py")
  exit
}

throw "Python not found. Install Python 3 and ensure 'py' or 'python' is available in PATH."
