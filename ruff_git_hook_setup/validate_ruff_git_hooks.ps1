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
$preCommitHookPath = Join-Path $hookDir "pre-commit"
$prePushHookPath = Join-Path $hookDir "pre-push"
$runnerPath = Join-Path $repoPath "ruff_git_hook_setup\run_ruff_git_hook.ps1"
$probeFile = Join-Path $repoPath "ruff_git_hook_setup\_ruff_hook_validation_bad.py"
$probeRelativePath = "ruff_git_hook_setup/_ruff_hook_validation_bad.py"
$gitExe = (Get-Command git.exe -ErrorAction Stop).Source
$gitRoot = Split-Path (Split-Path $gitExe -Parent) -Parent
$shExe = Join-Path $gitRoot "bin\sh.exe"
if (-not (Test-Path -LiteralPath $shExe -PathType Leaf)) {
    $shExe = Join-Path $gitRoot "usr\bin\sh.exe"
}
$report = [ordered]@{}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Command,
        [string]$InputText
    )

    $commandName = $Command[0]
    $commandArgs = @()
    if ($Command.Count -gt 1) {
        $commandArgs = $Command[1..($Command.Count - 1)]
    }

    if ($PSBoundParameters.ContainsKey("InputText")) {
        $output = $InputText | & $commandName @commandArgs 2>&1
    } else {
        $output = & $commandName @commandArgs 2>&1
    }

    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output = @($output)
    }
}

$report.repo = $repoPath
$report.pre_commit_hook_exists = Test-Path -LiteralPath $preCommitHookPath -PathType Leaf
$report.pre_push_hook_exists = Test-Path -LiteralPath $prePushHookPath -PathType Leaf
$report.hook_runner_exists = Test-Path -LiteralPath $runnerPath -PathType Leaf

Push-Location $repoPath
try {
    $allFilesRun = Invoke-CheckedCommand -Command @(
        "py", "-3.12", "-m", "uv", "run", "--with", "pre-commit", "pre-commit",
        "run", "ruff-check", "--config", (Join-Path $repoPath ".pre-commit-config.yaml"), "--all-files"
    )
    $report.pre_commit_run_all_files = [ordered]@{
        exit_code = $allFilesRun.ExitCode
        output = $allFilesRun.Output
    }

    $stagedPythonBefore = git -C $repoPath diff --cached --name-only --diff-filter=ACMR -- "*.py" "*.pyi"
    if ($stagedPythonBefore) {
        throw "Validation requires no pre-existing staged Python files; found staged Python content."
    }

    Set-Content -LiteralPath $probeFile -Encoding ascii -Value @(
        "import sys",
        "",
        "def broken() -> None:",
        '    print("probe")'
    )

    git -C $repoPath add -- $probeRelativePath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to stage validation probe file."
    }

    $preCommitRun = Invoke-CheckedCommand -Command @($shExe, $preCommitHookPath)
    $report.pre_commit_manual_probe = [ordered]@{
        exit_code = $preCommitRun.ExitCode
        output = $preCommitRun.Output
    }

    $prePushRun = Invoke-CheckedCommand -Command @(
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $runnerPath,
        "-HookType", "pre-push", "-Files", $probeRelativePath
    )
    $report.pre_push_manual_probe = [ordered]@{
        exit_code = $prePushRun.ExitCode
        output = $prePushRun.Output
    }
} finally {
    Pop-Location
    & git -C $repoPath rm --cached --quiet --ignore-unmatch -- $probeRelativePath 2>$null | Out-Null
    Remove-Item -LiteralPath $probeFile -Force -ErrorAction SilentlyContinue
}

[pscustomobject]$report
