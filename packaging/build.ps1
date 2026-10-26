$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venv = Join-Path $root ".venv"
$python = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Creating virtual environment..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $venv
    }
    else {
        & python -m venv $venv
    }
}

Write-Host "Installing build dependencies..."
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $root "requirements.txt")
& $python -m pip install -r (Join-Path $root "requirements-build.txt")

$icon = Join-Path $root "app\resources\icon.ico"
if (-not (Test-Path $icon)) {
    Write-Host "Generating application icon..."
    & $python (Join-Path $root "scripts\make_icon.py")
}

Write-Host "Running PyInstaller..."
& $python -m PyInstaller --noconfirm --clean (Join-Path $root "packaging\image_edit.spec")

$appDir = Join-Path $root "dist\ImageEdit"
$exe = Join-Path $appDir "ImageEdit.exe"
if (-not (Test-Path $exe)) {
    throw "Build failed: $exe was not produced."
}

Write-Host "Smoke testing the packaged app..."
$smoke = Start-Process -FilePath $exe -ArgumentList "--smoke-test" -Wait -PassThru
if ($smoke.ExitCode -ne 0) {
    throw "Packaged app failed its smoke test (exit code $($smoke.ExitCode))."
}

$zip = Join-Path $root "dist\ImageEdit-portable.zip"
if (Test-Path $zip) {
    Remove-Item $zip -Force
}
Compress-Archive -Path (Join-Path $appDir "*") -DestinationPath $zip

Write-Host ""
Write-Host "Portable build: $zip"
Write-Host "Executable:     $exe"
