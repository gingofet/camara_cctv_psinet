$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
$BuildVenv = Join-Path $ProjectRoot ".venv-build-windows"
$Python = Join-Path $BuildVenv "Scripts/python.exe"

Set-Location $ProjectRoot

if (-not (Test-Path $Python)) {
    python -m venv $BuildVenv
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt "pyinstaller==6.22.1"

& $Python -m unittest discover -s tests -v
& $Python -m compileall -q cctvflow tests cctvflow_gui.py

$env:PLAYWRIGHT_BROWSERS_PATH = "0"
& $Python -m playwright install chromium
& $Python -m PyInstaller --noconfirm --clean packaging/windows/CCTVFlow.spec

$Archive = Join-Path $ProjectRoot "dist/CCTVFlow-Windows-x64.zip"
if (Test-Path $Archive) {
    Remove-Item -LiteralPath $Archive
}
Compress-Archive -Path "dist/CCTVFlow" -DestinationPath $Archive

Write-Host "Paquete creado: $Archive"
