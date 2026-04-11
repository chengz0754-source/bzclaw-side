param(
    [string]$CommitMessage = "",
    [switch]$StageAll
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ExitCodes = @{
    SUCCESS = 0
    SUCCESS_WITH_NETWORK_WARNING = 10
    NO_CHANGES = 11
    REBASE_REQUIRED = 12
    UNSTAGED_BLOCK = 13
    WRONG_REPO = 14
    WRONG_BRANCH = 15
    NETWORK_UNSTABLE = 16
    PUSH_FAILED = 17
}

$LegacyOriginRepairMap = @{
    "E:\bzclaw side" = "https://github.com/chengz0754-source/bzclaw-side.git"
}

function Normalize-PathText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathText
    )

    return ([System.IO.Path]::GetFullPath($PathText)).TrimEnd("\")
}

function Invoke-GitCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $hasNativePreferenceSwitch = Test-Path Variable:PSNativeCommandUseErrorActionPreference
    if ($hasNativePreferenceSwitch) {
        $previousNativePreference = $PSNativeCommandUseErrorActionPreference
    }

    try {
        $ErrorActionPreference = "Continue"
        if ($hasNativePreferenceSwitch) {
            $PSNativeCommandUseErrorActionPreference = $false
        }

        $output = & git -C $RepoRoot @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
        if ($hasNativePreferenceSwitch) {
            $PSNativeCommandUseErrorActionPreference = $previousNativePreference
        }
    }

    $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = $text
        Arguments = ($Arguments -join " ")
    }
}

function Complete-Sync {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Code,
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [hashtable]$Details = [ordered]@{}
    )

    Write-Host ("RESULT_CODE={0}" -f $Code)
    Write-Host $Message
    foreach ($key in $Details.Keys) {
        Write-Host ("{0}={1}" -f $key, $Details[$key])
    }

    exit $ExitCodes[$Code]
}

function Get-RequiredGitText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$FailureCode,
        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    $result = Invoke-GitCommand -RepoRoot $RepoRoot -Arguments $Arguments
    if ($result.ExitCode -ne 0) {
        Complete-Sync -Code $FailureCode -Message $FailureMessage -Details ([ordered]@{
                git_command = $result.Arguments
                git_output = $result.Output
            })
    }

    return $result.Output
}

function Split-NonEmptyLines {
    param(
        [string]$Text
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return @()
    }

    return @(
        $Text -split "`r?`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object {
                $_ -and
                ($_ -notmatch "^warning: in the working copy of '.*', (LF|CRLF) will be replaced by (CRLF|LF) the next time Git touches it$")
            }
    )
}

function Test-NetworkIssue {
    param(
        [string]$Text
    )

    $patterns = @(
        "unable to access",
        "failed to connect",
        "connection timed out",
        "could not resolve host",
        "network is unreachable",
        "connection reset",
        "recv failure",
        "send failure",
        "tls",
        "ssl",
        "schannel",
        "port 443"
    )

    $lower = [string]::Concat($Text).ToLowerInvariant()
    foreach ($pattern in $patterns) {
        if ($lower.Contains($pattern)) {
            return $true
        }
    }

    return $false
}

function Test-PushRejected {
    param(
        [string]$Text
    )

    $patterns = @(
        "[rejected]",
        "non-fast-forward",
        "fetch first",
        "failed to push some refs",
        "remote contains work that you do not have locally"
    )

    $lower = [string]::Concat($Text).ToLowerInvariant()
    foreach ($pattern in $patterns) {
        if ($lower.Contains($pattern)) {
            return $true
        }
    }

    return $false
}

function Test-RebaseConflict {
    param(
        [string]$Text
    )

    $patterns = @(
        "conflict",
        "could not apply",
        "resolve all conflicts manually",
        "fix conflicts",
        "rebase in progress"
    )

    $lower = [string]::Concat($Text).ToLowerInvariant()
    foreach ($pattern in $patterns) {
        if ($lower.Contains($pattern)) {
            return $true
        }
    }

    return $false
}

function Get-DisplayRepoName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$OriginUrl
    )

    if (-not [string]::IsNullOrWhiteSpace($OriginUrl) -and $OriginUrl -match "/([^/]+?)(?:\.git)?$") {
        return $matches[1]
    }

    return (Split-Path -Path $RepoRoot -Leaf)
}

$scriptRepoRoot = Normalize-PathText (Join-Path $PSScriptRoot "..")
$repoProbe = Invoke-GitCommand -RepoRoot $scriptRepoRoot -Arguments @("rev-parse", "--show-toplevel")
if ($repoProbe.ExitCode -ne 0) {
    Complete-Sync -Code "WRONG_REPO" -Message "This script must run inside a git repo that contains it." -Details ([ordered]@{
            repo_root_candidate = $scriptRepoRoot
            git_output = $repoProbe.Output
        })
}

$repoRoot = Normalize-PathText $repoProbe.Output
if ($repoRoot -ne $scriptRepoRoot) {
    Complete-Sync -Code "WRONG_REPO" -Message "The script location does not match the active git repo root." -Details ([ordered]@{
            script_repo_root = $scriptRepoRoot
            git_repo_root = $repoRoot
        })
}

$branch = Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("branch", "--show-current") -FailureCode "WRONG_REPO" -FailureMessage "Could not read the current branch."
if ($branch -ne "main") {
    Complete-Sync -Code "WRONG_BRANCH" -Message "Only branch 'main' is supported by the universal sync entrypoint." -Details ([ordered]@{
            repo_root = $repoRoot
            branch = $branch
        })
}

$originUrl = (Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("remote", "get-url", "origin") -FailureCode "WRONG_REPO" -FailureMessage "This repo does not have a readable 'origin' remote.").Trim()
if ($LegacyOriginRepairMap.ContainsKey($originUrl)) {
    $repairedOrigin = $LegacyOriginRepairMap[$originUrl]
    $repairResult = Invoke-GitCommand -RepoRoot $repoRoot -Arguments @("remote", "set-url", "origin", $repairedOrigin)
    if ($repairResult.ExitCode -ne 0) {
        Complete-Sync -Code "PUSH_FAILED" -Message "Failed to repair the known legacy origin mapping." -Details ([ordered]@{
                repo_root = $repoRoot
                old_origin = $originUrl
                new_origin = $repairedOrigin
                git_output = $repairResult.Output
            })
    }
    $originUrl = $repairedOrigin
}

$repoName = Get-DisplayRepoName -RepoRoot $repoRoot -OriginUrl $originUrl
Write-Host ("Repo={0}" -f $repoName)
Write-Host ("RepoRoot={0}" -f $repoRoot)
Write-Host ("Branch={0}" -f $branch)
Write-Host ("Origin={0}" -f $originUrl)

$gitDirText = Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("rev-parse", "--git-dir") -FailureCode "WRONG_REPO" -FailureMessage "Could not resolve the git metadata directory."
$gitDir = $gitDirText
if (-not [System.IO.Path]::IsPathRooted($gitDir)) {
    $gitDir = Join-Path $repoRoot $gitDir
}
$gitDir = Normalize-PathText $gitDir

$unstaged = Split-NonEmptyLines (Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("diff", "--name-only") -FailureCode "PUSH_FAILED" -FailureMessage "Failed to inspect unstaged changes.")
$staged = Split-NonEmptyLines (Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("diff", "--cached", "--name-only") -FailureCode "PUSH_FAILED" -FailureMessage "Failed to inspect staged changes.")
$untracked = Split-NonEmptyLines (Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("ls-files", "--others", "--exclude-standard") -FailureCode "PUSH_FAILED" -FailureMessage "Failed to inspect untracked files.")

if (-not $StageAll -and (($unstaged.Count -gt 0) -or ($untracked.Count -gt 0))) {
    Complete-Sync -Code "UNSTAGED_BLOCK" -Message "Working tree changes were found. Stage explicitly or rerun with -StageAll." -Details ([ordered]@{
            unstaged_count = $unstaged.Count
            untracked_count = $untracked.Count
            unstaged_preview = (($unstaged | Select-Object -First 5) -join "; ")
            untracked_preview = (($untracked | Select-Object -First 5) -join "; ")
        })
}

if ($StageAll) {
    $stageResult = Invoke-GitCommand -RepoRoot $repoRoot -Arguments @("add", "-A")
    if ($stageResult.ExitCode -ne 0) {
        Complete-Sync -Code "PUSH_FAILED" -Message "git add -A failed." -Details ([ordered]@{
                git_output = $stageResult.Output
            })
    }

    $unstaged = Split-NonEmptyLines (Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("diff", "--name-only") -FailureCode "PUSH_FAILED" -FailureMessage "Failed to inspect unstaged changes after staging.")
    $staged = Split-NonEmptyLines (Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("diff", "--cached", "--name-only") -FailureCode "PUSH_FAILED" -FailureMessage "Failed to inspect staged changes after staging.")
    $untracked = Split-NonEmptyLines (Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("ls-files", "--others", "--exclude-standard") -FailureCode "PUSH_FAILED" -FailureMessage "Failed to inspect untracked files after staging.")
}

$aheadText = Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("rev-list", "--count", "origin/main..HEAD") -FailureCode "PUSH_FAILED" -FailureMessage "Could not compare local HEAD against origin/main."
$aheadCount = 0
[void][int]::TryParse($aheadText, [ref]$aheadCount)

if (($staged.Count -eq 0) -and ($unstaged.Count -eq 0) -and ($untracked.Count -eq 0) -and ($aheadCount -eq 0)) {
    Complete-Sync -Code "NO_CHANGES" -Message "No local changes or pending local commits were found." -Details ([ordered]@{
            repo = $repoName
            branch = $branch
        })
}

if (($staged.Count -eq 0) -and (($unstaged.Count -gt 0) -or ($untracked.Count -gt 0))) {
    Complete-Sync -Code "UNSTAGED_BLOCK" -Message "The repo still has local changes that are not staged." -Details ([ordered]@{
            unstaged_count = $unstaged.Count
            untracked_count = $untracked.Count
        })
}

if ($staged.Count -gt 0) {
    $resolvedMessage = if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
        "项目更新"
    } else {
        $CommitMessage.Trim()
    }

    $commitResult = Invoke-GitCommand -RepoRoot $repoRoot -Arguments @("commit", "-m", $resolvedMessage)
    if ($commitResult.ExitCode -ne 0) {
        Complete-Sync -Code "PUSH_FAILED" -Message "git commit failed." -Details ([ordered]@{
                commit_message = $resolvedMessage
                git_output = $commitResult.Output
            })
    }
}

$pushResult = Invoke-GitCommand -RepoRoot $repoRoot -Arguments @("push", "origin", "main")
if ($pushResult.ExitCode -eq 0) {
    $head = Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("rev-parse", "HEAD") -FailureCode "PUSH_FAILED" -FailureMessage "Push succeeded but HEAD could not be read afterward."
    $verifyResult = Invoke-GitCommand -RepoRoot $repoRoot -Arguments @("ls-remote", "--heads", "origin", "main")
    if ($verifyResult.ExitCode -ne 0 -and (Test-NetworkIssue -Text $verifyResult.Output)) {
        Complete-Sync -Code "SUCCESS_WITH_NETWORK_WARNING" -Message "Push succeeded, but remote verification hit a transient network issue." -Details ([ordered]@{
                repo = $repoName
                head = $head
                origin = $originUrl
                warning = $verifyResult.Output
            })
    }

    Complete-Sync -Code "SUCCESS" -Message "Push to origin/main succeeded." -Details ([ordered]@{
            repo = $repoName
            head = $head
            origin = $originUrl
        })
}

if (Test-PushRejected -Text $pushResult.Output) {
    $fetchResult = Invoke-GitCommand -RepoRoot $repoRoot -Arguments @("fetch", "origin", "main")
    if ($fetchResult.ExitCode -ne 0) {
        if (Test-NetworkIssue -Text $fetchResult.Output) {
            Complete-Sync -Code "NETWORK_UNSTABLE" -Message "Push was rejected and the follow-up fetch hit a network issue." -Details ([ordered]@{
                    repo = $repoName
                    origin = $originUrl
                    git_output = $fetchResult.Output
                })
        }

        Complete-Sync -Code "PUSH_FAILED" -Message "Push was rejected and follow-up fetch failed." -Details ([ordered]@{
                repo = $repoName
                origin = $originUrl
                git_output = $fetchResult.Output
            })
    }

    $rebaseResult = Invoke-GitCommand -RepoRoot $repoRoot -Arguments @("rebase", "origin/main")
    if ($rebaseResult.ExitCode -ne 0) {
        if (Test-NetworkIssue -Text $rebaseResult.Output) {
            Complete-Sync -Code "NETWORK_UNSTABLE" -Message "Push was rejected and the rebase attempt hit a network issue." -Details ([ordered]@{
                    repo = $repoName
                    origin = $originUrl
                    git_output = $rebaseResult.Output
                })
        }

        if ((Test-RebaseConflict -Text $rebaseResult.Output) -or (Test-Path (Join-Path $gitDir "rebase-merge")) -or (Test-Path (Join-Path $gitDir "rebase-apply"))) {
            Complete-Sync -Code "REBASE_REQUIRED" -Message "Rebase needs manual resolution before push can continue." -Details ([ordered]@{
                    repo = $repoName
                    origin = $originUrl
                    git_output = $rebaseResult.Output
                })
        }

        Complete-Sync -Code "PUSH_FAILED" -Message "Push was rejected and the automatic rebase step failed." -Details ([ordered]@{
                repo = $repoName
                origin = $originUrl
                git_output = $rebaseResult.Output
            })
    }

    $retryPush = Invoke-GitCommand -RepoRoot $repoRoot -Arguments @("push", "origin", "main")
    if ($retryPush.ExitCode -eq 0) {
        $head = Get-RequiredGitText -RepoRoot $repoRoot -Arguments @("rev-parse", "HEAD") -FailureCode "PUSH_FAILED" -FailureMessage "Push succeeded after rebase, but HEAD could not be read."
        Complete-Sync -Code "SUCCESS" -Message "Push to origin/main succeeded after fetch/rebase." -Details ([ordered]@{
                repo = $repoName
                head = $head
                origin = $originUrl
            })
    }

    if (Test-NetworkIssue -Text $retryPush.Output) {
        Complete-Sync -Code "NETWORK_UNSTABLE" -Message "Retry push failed because the network to origin was unstable." -Details ([ordered]@{
                repo = $repoName
                origin = $originUrl
                git_output = $retryPush.Output
            })
    }

    Complete-Sync -Code "PUSH_FAILED" -Message "Retry push failed after fetch/rebase." -Details ([ordered]@{
            repo = $repoName
            origin = $originUrl
            git_output = $retryPush.Output
        })
}

if (Test-NetworkIssue -Text $pushResult.Output) {
    Complete-Sync -Code "NETWORK_UNSTABLE" -Message "Push failed because the network to origin was unstable." -Details ([ordered]@{
            repo = $repoName
            origin = $originUrl
            git_output = $pushResult.Output
        })
}

Complete-Sync -Code "PUSH_FAILED" -Message "Push failed and was not eligible for automatic rebase recovery." -Details ([ordered]@{
        repo = $repoName
        origin = $originUrl
        git_output = $pushResult.Output
    })
