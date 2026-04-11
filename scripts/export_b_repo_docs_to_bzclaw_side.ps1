Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$targetRepoRoot = "E:\bzclaw-side"
$expectedSourceOrigin = "https://github.com/chengz0754-source/amazon-selection-automation.git"
$expectedTargetOrigin = "https://github.com/chengz0754-source/bzclaw-side.git"
$mirrorRoots = @(
    "README.md",
    "package.json",
    "requirements.txt",
    "configs/",
    "models/",
    "scripts/",
    "templates/",
    "skills/"
)

function Normalize-PathText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathText
    )

    return ([System.IO.Path]::GetFullPath($PathText)).TrimEnd('\')
}

function Get-GitText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $output = & git -C $RepoRoot @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git -C $RepoRoot $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }

    return (($output | Out-String).Trim())
}

function Test-MirrorCandidate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    foreach ($mirrorRoot in $mirrorRoots) {
        if ($mirrorRoot.EndsWith("/")) {
            if ($RelativePath.StartsWith($mirrorRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                return $true
            }
        } elseif ($RelativePath -ieq $mirrorRoot) {
            return $true
        }
    }

    return $false
}

$sourceRepoRoot = Normalize-PathText (Join-Path $PSScriptRoot "..")
$actualSourceRoot = Normalize-PathText (Get-GitText -RepoRoot $sourceRepoRoot -Arguments @("rev-parse", "--show-toplevel"))
if ($actualSourceRoot -ne (Normalize-PathText $sourceRepoRoot)) {
    throw "This script must run from the selection repo at $sourceRepoRoot."
}

$sourceOrigin = Get-GitText -RepoRoot $sourceRepoRoot -Arguments @("remote", "get-url", "origin")
if ($sourceOrigin -ne $expectedSourceOrigin) {
    throw "Unexpected selection origin: $sourceOrigin"
}

$targetOrigin = Get-GitText -RepoRoot $targetRepoRoot -Arguments @("remote", "get-url", "origin")
if ($targetOrigin -ne $expectedTargetOrigin) {
    throw "Unexpected b-side origin: $targetOrigin"
}

$trackedFiles = @(& git -C $sourceRepoRoot ls-files)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to list tracked files in the selection repo."
}

$mirrorFiles = $trackedFiles | Where-Object { Test-MirrorCandidate -RelativePath $_ }
if ($mirrorFiles.Count -eq 0) {
    throw "No tracked mirror files matched the current export allowlist."
}

foreach ($relativePath in $mirrorFiles) {
    $sourcePath = Join-Path $sourceRepoRoot $relativePath
    $targetPath = Join-Path $targetRepoRoot $relativePath
    $targetDirectory = Split-Path -Parent $targetPath

    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Missing tracked source file: $sourcePath"
    }

    if (-not (Test-Path -LiteralPath $targetDirectory)) {
        New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null
    }

    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
}

Write-Host "Mirrored $($mirrorFiles.Count) selection-owned tracked files into $targetRepoRoot"
