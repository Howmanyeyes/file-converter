param([string]$Version = "")

& (Join-Path $PSScriptRoot "_build_installer.ps1") `
    -Edition full `
    -Architecture amd64 `
    -Version $Version
