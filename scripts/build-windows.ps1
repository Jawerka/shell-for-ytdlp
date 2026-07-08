#Requires -Version 5.1
<#
.SYNOPSIS
  Build UI-for-ytdlp Windows release, zip, and Inno Setup installer.

.PARAMETER OutputDir
  Folder for UI-for-ytdlp-<version>-windows-x64.zip and setup.exe.
  Defaults to dist/.

.EXAMPLE
  .\scripts\build-windows.ps1
#>
param(
    [string] $OutputDir = "",
    [switch] $Run
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if ([string]::IsNullOrWhiteSpace($OutputDir)) {
        $OutputDir = Join-Path $root "dist"
    }
    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }
    $outputDirResolved = (Resolve-Path -LiteralPath $OutputDir).Path

    Write-Host "Building UI-for-ytdlp with PyInstaller..."
    $venvPython = Join-Path $root "venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        & $venvPython build.py
    } else {
        python build.py
    }
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    $releaseDir = Join-Path $outputDirResolved "UI-for-ytdlp"
    $releaseExe = Join-Path $releaseDir "UI-for-ytdlp.exe"
    $utilitiesDir = Join-Path $releaseDir "utilities"
    if (-not (Test-Path $releaseExe)) {
        throw "Release binary not found: $releaseExe"
    }
    if (-not (Test-Path $utilitiesDir)) {
        throw "utilities/ folder not found: $utilitiesDir"
    }

    $version = & (Join-Path $PSScriptRoot "read-app-version.ps1")
    $zipName = "UI-for-ytdlp-$version-windows-x64.zip"
    $zipPath = Join-Path $outputDirResolved $zipName

    Write-Host "Packaging $zipName..."
    if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
    tar -a -cf $zipPath -C $outputDirResolved "UI-for-ytdlp"

    Write-Host "Building Windows installer..."
    & (Join-Path $PSScriptRoot "package-windows-installer.ps1") `
        -Version $version `
        -ReleaseDir $outputDirResolved `
        -OutputDir $outputDirResolved

    $setupPath = Join-Path $outputDirResolved "UI-for-ytdlp-$version-windows-x64-setup.exe"
    Write-Host ""
    Write-Host "Windows release artifacts:" -ForegroundColor Green
    Write-Host "  $releaseDir\"
    Write-Host "  $zipPath"
    Write-Host "  $setupPath"

    if ($Run) {
        Write-Host ""
        Write-Host "Starting $releaseExe" -ForegroundColor Green
        & $releaseExe
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}
