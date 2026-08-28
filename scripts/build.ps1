$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$packagingPython = Join-Path $projectRoot ".venv-packaging\Scripts\python.exe"
$developmentPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pythonExecutable = if (Test-Path -LiteralPath $packagingPython) {
    $packagingPython
}
else {
    $developmentPython
}

if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw "Virtual environment not found. Create .venv-packaging or .venv first."
}

Push-Location $projectRoot
$originalPath = $env:PATH
try {
    # Build tools may prepend unrelated native-library folders to PATH. In
    # particular, Poppler's ICU DLLs have the same names as the Windows ICU
    # shims used by Qt, but expose a different ABI. Do not let PyInstaller
    # mistake those toolchain DLLs for application dependencies.
    $env:PATH = (($originalPath -split ";") | Where-Object {
        $_ -and $_ -notmatch "[\\/]\.cache[\\/]codex-runtimes[\\/]"
    }) -join ";"

    & $pythonExecutable -m PyInstaller --noconfirm --clean MijiaDesktop.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE"
    }
    Write-Host "Built: $projectRoot\dist\MijiaDesktop.exe"
}
finally {
    $env:PATH = $originalPath
    Pop-Location
}
