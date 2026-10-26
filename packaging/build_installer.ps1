$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$exe = Join-Path $root "dist\ImageEdit\ImageEdit.exe"
if (-not (Test-Path $exe)) {
    throw "Run packaging\build.ps1 first; dist\ImageEdit\ImageEdit.exe is missing."
}

$iscc = (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    foreach ($candidate in @(
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            "C:\Program Files\Inno Setup 6\ISCC.exe"
        )) {
        if (Test-Path $candidate) {
            $iscc = $candidate
            break
        }
    }
}
if (-not $iscc) {
    throw "Inno Setup not found. Install it with: winget install -e --id JRSoftware.InnoSetup"
}

$python = Join-Path $root ".venv\Scripts\python.exe"
$version = (& $python -c "import app; print(app.__version__)").Trim()

& $iscc "/DMyAppVersion=$version" (Join-Path $PSScriptRoot "installer.iss")
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE."
}

$setup = Join-Path $root "dist\ImageEdit-Setup-$version.exe"
Write-Host "Installer: $setup"
