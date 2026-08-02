[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("arm64", "amd64")]
    [string]$Architecture,

    [Parameter(Mandatory = $true)]
    [string]$Destination
)

$ErrorActionPreference = "Stop"
$RootDirectory = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$LibreOfficeVersion = "26.2.4"

if ($Architecture -eq "arm64") {
    $ArchiveName = "LibreOffice_26.2.4_Win_aarch64.msi"
    $ArchiveFolder = "aarch64"
    $ExpectedHash = "1cd35d4d2821f6b6e7e65a2fc7c0faa2b5074ecd0ad90c5eb30af8a4f86d3b0d"
} else {
    $ArchiveName = "LibreOffice_26.2.4_Win_x86-64.msi"
    $ArchiveFolder = "x86_64"
    $ExpectedHash = "202f26cda071c5aa4996a5a28412fddceb3891dceb0366982c62650456c0730f"
}

$ArchiveUrl = "https://download.documentfoundation.org/libreoffice/stable/$LibreOfficeVersion/win/$ArchiveFolder/$ArchiveName"
$CacheDirectory = Join-Path $RootDirectory ".cache/libreoffice/windows-$Architecture"
$ArchivePath = Join-Path $CacheDirectory $ArchiveName
$ExtractionDirectory = Join-Path $RootDirectory "build/libreoffice-$Architecture-extracted"

New-Item -ItemType Directory -Force -Path $CacheDirectory | Out-Null
if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
    Write-Host "Downloading LibreOffice $LibreOfficeVersion for Windows $Architecture..."
    Invoke-WebRequest -Uri $ArchiveUrl -OutFile $ArchivePath
}

$ActualHash = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualHash -ne $ExpectedHash) {
    throw "LibreOffice checksum mismatch. Expected $ExpectedHash, got $ActualHash."
}

Remove-Item -LiteralPath $ExtractionDirectory -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $ExtractionDirectory | Out-Null

$MsiArguments = @(
    "/a",
    "`"$ArchivePath`"",
    "/qn",
    "TARGETDIR=`"$ExtractionDirectory`""
)
$MsiProcess = Start-Process -FilePath "msiexec.exe" -ArgumentList $MsiArguments -Wait -PassThru
if ($MsiProcess.ExitCode -ne 0) {
    throw "LibreOffice extraction failed with exit code $($MsiProcess.ExitCode)."
}

$Soffice = Get-ChildItem -LiteralPath $ExtractionDirectory -Filter "soffice.exe" -File -Recurse |
    Where-Object { $_.Directory.Name -eq "program" } |
    Select-Object -First 1
if ($null -eq $Soffice) {
    throw "LibreOffice extraction did not produce program/soffice.exe."
}

$RuntimeSource = $Soffice.Directory.Parent.FullName
Remove-Item -LiteralPath $Destination -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item -LiteralPath $RuntimeSource -Destination $Destination -Recurse -Force
Remove-Item -LiteralPath $ExtractionDirectory -Recurse -Force

$BundledSoffice = Join-Path $Destination "program/soffice.exe"
if (-not (Test-Path -LiteralPath $BundledSoffice -PathType Leaf)) {
    throw "LibreOffice runtime was not copied to the application."
}

Write-Host "LibreOffice runtime prepared: $Destination"
