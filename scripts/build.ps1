$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$packagingPython = Join-Path $projectRoot ".venv-packaging\Scripts\python.exe"
$developmentPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pythonExecutable = $null

foreach ($candidate in @($packagingPython, $developmentPython)) {
    if (-not (Test-Path -LiteralPath $candidate)) {
        continue
    }
    $environmentRoot = Split-Path -Parent (Split-Path -Parent $candidate)
    $configuration = Join-Path $environmentRoot "pyvenv.cfg"
    if (Test-Path -LiteralPath $configuration) {
        $homeSetting = Get-Content -LiteralPath $configuration |
            Where-Object { $_ -match '^home\s*=' } |
            Select-Object -First 1
        if ($homeSetting) {
            $basePython = (Split-Path -Leaf $candidate)
            $baseDirectory = ($homeSetting -split '=', 2)[1].Trim()
            if (-not (Test-Path -LiteralPath (Join-Path $baseDirectory $basePython))) {
                continue
            }
        }
    }
    try {
        & $candidate -c "import PyInstaller" 2>$null
    }
    catch {
        continue
    }
    if ($LASTEXITCODE -eq 0) {
        $pythonExecutable = $candidate
        break
    }
}

if ($null -eq $pythonExecutable) {
    throw "No working virtual environment with PyInstaller was found."
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
    Write-Host "Built: $projectRoot\dist\MijiaDesktop-0.1.0-alpha.exe"
}
finally {
    $env:PATH = $originalPath
    Pop-Location
}
