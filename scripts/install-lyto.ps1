$ErrorActionPreference = "Stop"

$py = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $py) {
  throw "Python launcher 'py' not found. Install Python 3 and ensure 'py' is available."
}

Write-Host "Installing lyto (QR wireless ADB helper)..." -ForegroundColor Cyan
Write-Host "This downloads packages from the internet via pip." -ForegroundColor Yellow

& py -3 -m pip install --upgrade pip
& py -3 -m pip install "git+https://github.com/eeriemyxi/lyto@main"

Write-Host "Done. You can now run scripts\\lyto-qr.ps1" -ForegroundColor Green
