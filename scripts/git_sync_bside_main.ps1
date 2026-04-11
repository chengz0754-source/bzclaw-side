param(
    [string]$CommitMessage = "",
    [switch]$StageAll
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$expectedOrigin = "https://github.com/chengz0754-source/bzclaw-side.git"
$legacyMirrorOrigin = "E:\bzclaw side"

function Normalize-PathText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathText
    )

    return ([System.IO.Path]::GetFullPath($PathText)).TrimEnd('\')
}

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & git -C $expectedRepoRoot @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Get-GitText {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $output = & git -C $expectedRepoRoot @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }

    return (($output | Out-String).Trim())
}

$expectedRepoRoot = Normalize-PathText (Join-Path $PSScriptRoot "..")
$repoRoot = Normalize-PathText (Get-GitText -Arguments @("rev-parse", "--show-toplevel"))
$normalizedExpectedRepoRoot = Normalize-PathText $expectedRepoRoot
if ($repoRoot -ne $normalizedExpectedRepoRoot) {
    throw "This script only runs inside $expectedRepoRoot. Current repo root: $repoRoot"
}

Set-Location $expectedRepoRoot

$branch = Get-GitText -Arguments @("branch", "--show-current")
if ($branch -ne "main") {
    throw "Current branch is '$branch'. Switch to 'main' before syncing."
}

$originUrl = Get-GitText -Arguments @("remote", "get-url", "origin")
if ($originUrl -eq $legacyMirrorOrigin) {
    Write-Host "origin currently points to the legacy local mirror. Repairing it to GitHub..."
    Invoke-Git -Arguments @("remote", "set-url", "origin", $expectedOrigin)
    $originUrl = Get-GitText -Arguments @("remote", "get-url", "origin")
}

if ($originUrl -ne $expectedOrigin) {
    throw "origin must be $expectedOrigin. Current origin: $originUrl"
}

$unstaged = @(& git -C $expectedRepoRoot diff --name-only)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to inspect unstaged changes."
}

if ($unstaged.Count -gt 0) {
    Write-Host "Detected unstaged changes. Review and stage them first, then rerun:"
    $unstaged | ForEach-Object { Write-Host " - $_" }
    exit 1
}

if ($StageAll) {
    Write-Host "Staging all repo-visible changes in $expectedRepoRoot ..."
    Invoke-Git -Arguments @("add", "--all", "--", ".")
}

$staged = @(& git -C $expectedRepoRoot diff --cached --name-only)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to inspect staged changes."
}

$untracked = @(& git -C $expectedRepoRoot ls-files --others --exclude-standard)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to inspect untracked files."
}

if ($staged.Count -eq 0 -and $untracked.Count -gt 0) {
    Write-Host "Detected untracked files but no staged changes."
    Write-Host "Review them and run an explicit 'git add', or rerun with -StageAll."
    $untracked | ForEach-Object { Write-Host " - $_" }
    exit 1
}

if ($staged.Count -gt 0) {
    if ($untracked.Count -gt 0) {
        Write-Host "Warning: untracked files remain outside this commit."
        $untracked | ForEach-Object { Write-Host " - $_" }
    }

    $resolvedMessage = if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
        "项目更新"
    } else {
        $CommitMessage.Trim()
    }

    Write-Host "Creating commit: $resolvedMessage"
    Invoke-Git -Arguments @("commit", "-m", $resolvedMessage)
}

Write-Host "Pulling latest origin/main with rebase..."
Invoke-Git -Arguments @("pull", "--rebase", "origin", "main")

Write-Host "Pushing to origin/main..."
Invoke-Git -Arguments @("push", "origin", "main")

$head = Get-GitText -Arguments @("rev-parse", "HEAD")
Write-Host "Sync complete. HEAD = $head"
