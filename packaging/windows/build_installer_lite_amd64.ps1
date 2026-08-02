param([string]$Version = "")

& (Join-Path $PSScriptRoot "_build_installer.ps1") `
    -Edition lite `
    -Architecture amd64 `
    -Version $Version
