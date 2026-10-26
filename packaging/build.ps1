$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venv = Join-Path $root ".venv"
$python = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Creating virtual environment..."
    if ($env:PYTHON) {
        & $env:PYTHON -m venv $venv
    }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $venv
    }
    else {
        & python -m venv $venv
    }
}
if (-not (Test-Path $python)) {
    throw "Could not create the virtual environment at $venv."
}

Write-Host "Installing build dependencies..."
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
& $python -m pip install -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Failed to install runtime dependencies." }
& $python -m pip install -r (Join-Path $root "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "Failed to install build dependencies." }

$icon = Join-Path $root "app\resources\icon.ico"
if (-not (Test-Path $icon)) {
    Write-Host "Generating application icon..."
    & $python (Join-Path $root "scripts\make_icon.py")
    if ($LASTEXITCODE -ne 0) { throw "Failed to generate the application icon." }
}

Write-Host "Running PyInstaller..."
& $python -m PyInstaller --noconfirm --clean (Join-Path $root "packaging\image_edit.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE." }

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
