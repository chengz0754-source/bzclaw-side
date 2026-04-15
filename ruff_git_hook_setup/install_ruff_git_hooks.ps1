[CmdletBinding()]
param(
    [string]$TargetRepoPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($TargetRepoPath)) {
    $TargetRepoPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
}

$repoPath = (Resolve-Path -LiteralPath $TargetRepoPath).Path
$hookDir = Join-Path $repoPath ".git\hooks"
$runnerPath = Join-Path $repoPath "ruff_git_hook_setup\run_ruff_git_hook.ps1"
$configPath = Join-Path $repoPath ".pre-commit-config.yaml"
$preCommitHookPath = Join-Path $hookDir "pre-commit"
$prePushHookPath = Join-Path $hookDir "pre-push"
$backupSuffix = Get-Date -Format "yyyyMMddHHmmss"
$wrapperHeader = "# bzclaw-ruff-hook-wrapper"
$powershellExe = "/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"

function Assert-Command {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Command
    )

    & $Command[0] $Command[1..($Command.Count - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $($Command -join ' ')"
    }
}

function Backup-ExistingHook {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return
    }

    $current = Get-Content -LiteralPath $Path -Raw
    if ($current -match [regex]::Escape($wrapperHeader)) {
        return
    }

    Move-Item -LiteralPath $Path -Destination "$Path.bak.$backupSuffix"
}

function Write-HookWrapper {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HookPath,
        [Parameter(Mandatory = $true)]
        [string]$HookType
    )

    $content = @'
#!/bin/sh
{0}
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 1
RUNNER="$REPO_ROOT/ruff_git_hook_setup/run_ruff_git_hook.ps1"
exec "{1}" -NoProfile -ExecutionPolicy Bypass -File "$RUNNER" -HookType {2} "$@"
'@ -f $wrapperHeader, $powershellExe, $HookType

    Set-Content -LiteralPath $HookPath -Value $content -Encoding ascii
}

if (-not (Test-Path -LiteralPath $hookDir -PathType Container)) {
    throw "Missing hook directory: $hookDir"
}

if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Missing pre-commit config: $configPath"
}

if (-not (Test-Path -LiteralPath $runnerPath -PathType Leaf)) {
    throw "Missing hook runner: $runnerPath"
}

Assert-Command -Command @("git", "-C", $repoPath, "rev-parse", "--is-inside-work-tree")
Assert-Command -Command @("py", "-3.12", "--version")
Assert-Command -Command @("py", "-3.12", "-m", "uv", "--version")
Assert-Command -Command @("py", "-3.12", "-m", "uv", "run", "--with", "ruff", "ruff", "--version")
Assert-Command -Command @("py", "-3.12", "-m", "uv", "tool", "install", "pre-commit")

Backup-ExistingHook -Path $preCommitHookPath
Backup-ExistingHook -Path $prePushHookPath
Write-HookWrapper -HookPath $preCommitHookPath -HookType "pre-commit"
Write-HookWrapper -HookPath $prePushHookPath -HookType "pre-push"

Write-Output "Installed Ruff Git hooks in $repoPath"
Write-Output " - $preCommitHookPath"
Write-Output " - $prePushHookPath"
