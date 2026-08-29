$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$version = "1.0.0"
$executable = Join-Path $projectRoot "dist\MijiaDesktop-$version.exe"
$releaseRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "build\release"))
$stageDirectory = [System.IO.Path]::GetFullPath(
    (Join-Path $releaseRoot "MijiaDesktop-$version-win-x64")
)
$archive = Join-Path $projectRoot "dist\MijiaDesktop-$version-win-x64.zip"
$checksum = "$archive.sha256"

if (-not (Test-Path -LiteralPath $executable)) {
    throw "Release executable not found: $executable. Run scripts\build.ps1 first."
}

$buildInputs = @(
    Get-ChildItem -LiteralPath (Join-Path $projectRoot "app") -Recurse -File
    Get-ChildItem -LiteralPath (Join-Path $projectRoot "resources") -Recurse -File
    Get-Item -LiteralPath (Join-Path $projectRoot "MijiaDesktop.spec")
    Get-Item -LiteralPath (Join-Path $projectRoot "packaging\windows_version_info.txt")
)
$latestInput = $buildInputs | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
if ((Get-Item -LiteralPath $executable).LastWriteTimeUtc -lt $latestInput.LastWriteTimeUtc) {
    throw "Release executable is older than $($latestInput.FullName). Run scripts\build.ps1 first."
}

$releasePrefix = $releaseRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) +
    [System.IO.Path]::DirectorySeparatorChar
if (-not $stageDirectory.StartsWith($releasePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe release staging directory: $stageDirectory"
}
if (Test-Path -LiteralPath $stageDirectory) {
    Remove-Item -LiteralPath $stageDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $stageDirectory -Force | Out-Null
$documentationDirectory = Join-Path $stageDirectory "docs"
New-Item -ItemType Directory -Path $documentationDirectory -Force | Out-Null

Copy-Item -LiteralPath $executable -Destination $stageDirectory
Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $stageDirectory
Copy-Item -LiteralPath (Join-Path $projectRoot "LICENSE") -Destination $stageDirectory
Copy-Item -LiteralPath (Join-Path $projectRoot "RELEASE_NOTES.md") -Destination $stageDirectory
Copy-Item -LiteralPath (Join-Path $projectRoot "docs\KNOWN_ISSUES.md") `
    -Destination $documentationDirectory
Copy-Item -LiteralPath (Join-Path $projectRoot "docs\SUPPORTED_DEVICES.md") `
    -Destination $documentationDirectory

Compress-Archive -LiteralPath $stageDirectory -DestinationPath $archive -Force
$hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $(Split-Path -Leaf $archive)" | Set-Content -LiteralPath $checksum -Encoding ascii

Write-Host "Release archive: $archive"
Write-Host "SHA-256: $hash"
