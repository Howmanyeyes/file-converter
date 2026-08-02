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
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version must contain three numeric parts, for example 1.0.1."
}

$ActualArchitecture = (& python -c "import platform; print(platform.machine().lower())").Trim()
if ($ActualArchitecture -ne $Architecture) {
    throw "This build requires $Architecture Python, current architecture is $ActualArchitecture."
}

$PythonVersion = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if ($LASTEXITCODE -ne 0 -or $PythonVersion -ne "3.13") {
    throw "Windows builds require Python 3.13."
}

$EditionFile = Join-Path $RootDirectory "packaging/editions/$Edition.txt"
$IconSource = Join-Path $RootDirectory "assets/app-icon.png"
$IconFile = Join-Path $RootDirectory "assets/app-icon.ico"
$OutputDirectory = Join-Path $RootDirectory "build/windows-$Architecture-$Edition"
$GeneratedDistribution = Join-Path $OutputDirectory "main.dist"

if ($Edition -eq "full") {
    $AppName = "Offline File Converter"
    $ExecutableName = "OfflineFileConverter.exe"
} else {
    $AppName = "Offline File Converter Lite"
    $ExecutableName = "OfflineFileConverterLite.exe"
}

& python (Join-Path $PSScriptRoot "create_icon.py") $IconSource $IconFile
if ($LASTEXITCODE -ne 0) {
    throw "Windows icon generation failed."
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
Remove-Item -LiteralPath $GeneratedDistribution -Recurse -Force -ErrorAction SilentlyContinue

$NuitkaArguments = @(
    "--standalone",
    "--enable-plugin=pyside6",
    "--msvc=latest",
    "--windows-console-mode=disable",
    "--windows-icon-from-ico=$IconFile",
    "--product-name=$AppName",
    "--file-description=$AppName",
    "--file-version=$Version",
    "--product-version=$Version",
    "--output-filename=$ExecutableName",
    "--assume-yes-for-downloads",
    "--include-package=offline_file_converter",
    "--include-data-dir=$(Join-Path $RootDirectory 'src/offline_file_converter/resources')=offline_file_converter/resources",
    "--include-data-files=$EditionFile=offline_file_converter/resources/edition.txt",
    "--output-dir=$OutputDirectory",
    (Join-Path $RootDirectory "main.py")
)

$env:PYTHONPATH = Join-Path $RootDirectory "src"
$env:NUITKA_CACHE_DIR = Join-Path $RootDirectory ".cache/nuitka"
& python -m nuitka @NuitkaArguments
if ($LASTEXITCODE -ne 0) {
    throw "Nuitka failed to build $Edition Windows $Architecture application."
}

$ExecutablePath = Join-Path $GeneratedDistribution $ExecutableName
if (-not (Test-Path -LiteralPath $ExecutablePath -PathType Leaf)) {
    throw "Nuitka did not create $ExecutablePath."
}

if ($Edition -eq "full") {
    & (Join-Path $PSScriptRoot "prepare_libreoffice.ps1") `
        -Architecture $Architecture `
        -Destination (Join-Path $GeneratedDistribution "libreoffice")
}

Write-Host "Application built: $GeneratedDistribution"
