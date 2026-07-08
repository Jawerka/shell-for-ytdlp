# Builds UI-for-ytdlp-<version>-windows-x64-setup.exe via Inno Setup 6.
param(
    [Parameter(Mandatory)]
    [string]$Version,
    [Parameter(Mandatory)]
    [string]$ReleaseDir,
    [string]$OutputDir = ".",
    [string]$IssFile
)

$ErrorActionPreference = 'Stop'

if (-not $IssFile) {
    $IssFile = Join-Path $PSScriptRoot 'windows\ui-for-ytdlp.iss'
}

$releasePath = Resolve-Path $ReleaseDir
$appDir = Join-Path $releasePath 'UI-for-ytdlp'
$exe = Join-Path $appDir 'UI-for-ytdlp.exe'
$utilities = Join-Path $appDir 'utilities'

if (-not (Test-Path $exe)) {
    throw "Release build not found: $exe (run python build.py first)"
}
if (-not (Test-Path $utilities)) {
    throw "utilities/ folder not found: $utilities (build scaffold missing)"
}

$outputPath = Resolve-Path -LiteralPath $OutputDir -ErrorAction SilentlyContinue
if (-not $outputPath) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    $outputPath = Resolve-Path $OutputDir
}

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw @"
Inno Setup 6 not found. Install from https://jrsoftware.org/isinfo.php
  choco install innosetup -y
"@
}

Write-Host "Packaging UI-for-ytdlp $Version from $appDir"
& $iscc $IssFile `
    "/DMyAppVersion=$Version" `
    "/DReleaseDir=$releasePath" `
    "/DOutputDir=$outputPath"

$setup = Join-Path $outputPath "UI-for-ytdlp-$Version-windows-x64-setup.exe"
if (-not (Test-Path $setup)) {
    throw "Installer was not created: $setup"
}
Write-Host "Created $setup"
