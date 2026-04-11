Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$expectedSourceOrigin = "https://github.com/chengz0754-source/bzclaw-side.git"
$expectedTargetOrigin = "https://github.com/chengz0754-source/amazon-selection-automation.git"
$relativeFiles = @(
    "B_CANONICAL_FOLDER_DECISION.md",
    "DUAL_REPO_OWNERSHIP_MAP.csv",
    "DUAL_REPO_SYNC_RULES.md",
    "DUAL_REPO_GITIGNORE_RULES.md"
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

function Resolve-SelectionRepoRoot {
    $candidate = Get-ChildItem -Path "E:\" -Directory |
        ForEach-Object { Join-Path $_.FullName "amazon-selection-automation" } |
        Where-Object { Test-Path -LiteralPath $_ -PathType Container } |
        Select-Object -First 1

    if (-not $candidate) {
        throw "Could not find the selection repo root under E:\\"
    }

    return (Normalize-PathText $candidate)
}

$sourceRepoRoot = Normalize-PathText (Join-Path $PSScriptRoot "..")
$targetRepoRoot = Resolve-SelectionRepoRoot
$sourceFolder = Join-Path $sourceRepoRoot "reports\governance\20260412-b76-dual-repo-sync"
$targetFolder = Join-Path $targetRepoRoot "reports\governance\20260412-b76-dual-repo-sync"

$actualSourceRoot = Normalize-PathText (Get-GitText -RepoRoot $sourceRepoRoot -Arguments @("rev-parse", "--show-toplevel"))
if ($actualSourceRoot -ne (Normalize-PathText $sourceRepoRoot)) {
    throw "This script must run from the canonical b-side repo at $sourceRepoRoot."
}

$sourceOrigin = Get-GitText -RepoRoot $sourceRepoRoot -Arguments @("remote", "get-url", "origin")
if ($sourceOrigin -ne $expectedSourceOrigin) {
    throw "Unexpected b-side origin: $sourceOrigin"
}

$targetOrigin = Get-GitText -RepoRoot $targetRepoRoot -Arguments @("remote", "get-url", "origin")
if ($targetOrigin -ne $expectedTargetOrigin) {
    throw "Unexpected selection origin: $targetOrigin"
}

New-Item -ItemType Directory -Force -Path $targetFolder | Out-Null

foreach ($relativeFile in $relativeFiles) {
    $sourcePath = Join-Path $sourceFolder $relativeFile
    $targetPath = Join-Path $targetFolder $relativeFile

    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Missing source governance file: $sourcePath"
    }

    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
    Write-Host "Mirrored $relativeFile to selection repo governance folder."
}

Write-Host "Governance mirror export complete."
