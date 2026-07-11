# Build a Windows installer for NoRefund.
#
# Prerequisites:
#   - Run from an activated venv with the project installed: pip install -e .[dev]
#   - Inno Setup 6 installed, with `iscc` on PATH
#     (https://jrsoftware.org/isdl.php)
#
# Usage (from repo root, in PowerShell):
#   .\packaging\windows\build.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path "$PSScriptRoot\..\.."

Push-Location $RepoRoot
try {
    Write-Host "== Cleaning previous build output ==" -ForegroundColor Cyan
    Remove-Item -Recurse -Force "dist", "build" -ErrorAction SilentlyContinue

    Write-Host "== Running PyInstaller ==" -ForegroundColor Cyan
    pyinstaller packaging\norefund.spec --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

    if (-not (Get-Command iscc -ErrorAction SilentlyContinue)) {
        Write-Warning "iscc not found on PATH — skipping installer step."
        Write-Warning "Install Inno Setup 6 (https://jrsoftware.org/isdl.php) to build the .exe installer."
        Write-Host "PyInstaller output is ready at dist\NoRefund\NoRefund.exe" -ForegroundColor Green
        exit 0
    }

    Write-Host "== Running Inno Setup ==" -ForegroundColor Cyan
    iscc packaging\windows\installer.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup compile failed" }

    Write-Host "== Done ==" -ForegroundColor Green
    Write-Host "Installer: packaging\windows\dist\NoRefund-Setup-*.exe"
}
finally {
    Pop-Location
}
