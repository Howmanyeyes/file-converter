param([string]$Version = "")

& (Join-Path $PSScriptRoot "_build_installer.ps1") `
    -Edition lite `
    -Architecture arm64 `
    -Version $Version
