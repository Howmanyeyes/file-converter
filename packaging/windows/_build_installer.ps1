[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("full", "lite")]
    [string]$Edition,

    [Parameter(Mandatory = $true)]
    [ValidateSet("arm64", "amd64")]
    [string]$Architecture,

    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$RootDirectory = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Get-Content -LiteralPath (Join-Path $RootDirectory "packaging/version.txt") -Raw).Trim()
}

& (Join-Path $PSScriptRoot "_build_app.ps1") `
    -Edition $Edition `
    -Architecture $Architecture `
    -Version $Version

$SourceDirectory = Join-Path $RootDirectory "build/windows-$Architecture-$Edition/main.dist"
$OutputDirectory = Join-Path $RootDirectory "dist"
$IconFile = Join-Path $RootDirectory "assets/app-icon.ico"
$InstallerScript = Join-Path $PSScriptRoot "installer.iss"

$InnoCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 7/ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 7/ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6/ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6/ISCC.exe")
)
$InnoCompiler = $InnoCandidates |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1
if ([string]::IsNullOrWhiteSpace($InnoCompiler)) {
    $InnoCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($null -ne $InnoCommand) {
        $InnoCompiler = $InnoCommand.Source
    }
}
if ([string]::IsNullOrWhiteSpace($InnoCompiler)) {
    throw "Inno Setup 6 or 7 is required to build the installer."
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
& $InnoCompiler `
    "/DEdition=$Edition" `
    "/DArchitecture=$Architecture" `
    "/DAppVersion=$Version" `
    "/DSourceDir=$SourceDirectory" `
    "/DOutputDir=$OutputDirectory" `
    "/DIconFile=$IconFile" `
    $InstallerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed to build $Edition Windows $Architecture installer."
}

$InstallerPath = Join-Path $OutputDirectory "OfflineFileConverter-$Version-$Edition-windows-$Architecture-setup.exe"
if (-not (Test-Path -LiteralPath $InstallerPath -PathType Leaf)) {
    throw "Installer was not created: $InstallerPath"
}

$InstallerHash = (Get-FileHash -LiteralPath $InstallerPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "Installer built: $InstallerPath"
Write-Host "SHA256: $InstallerHash"
