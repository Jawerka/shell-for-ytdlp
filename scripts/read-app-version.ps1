# Prints semver from VERSION file at repository root.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$versionFile = Join-Path $root 'VERSION'
if (-not (Test-Path $versionFile)) {
    throw "VERSION file not found: $versionFile"
}
$semver = (Get-Content $versionFile -Raw).Trim()
if ($semver -notmatch '^\d+\.\d+\.\d+') {
    throw "Invalid VERSION format: $semver"
}
Write-Output $semver
