[CmdletBinding()]
param(
    [string]$RepoRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$env:NODE_OPTIONS = "--dns-result-order=ipv4first"
$env:NODE_NO_WARNINGS = "1"

$ControlRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProbeScript = Join-Path $ControlRoot "probe_and_bind_repo.ps1"
$NodeRoot = Join-Path $env:LOCALAPPDATA "BZCLAWToolchain\node\current"
$PyScripts = Join-Path $env:APPDATA "Python\Python312\Scripts"
$LocalBin = Join-Path $env:USERPROFILE ".local\bin"
$PnpmCmd = Join-Path $NodeRoot "pnpm.cmd"

function Add-PathCandidate {
    param([string]$PathEntry)

    if ([string]::IsNullOrWhiteSpace($PathEntry)) {
        return
    }

    $normalized = $PathEntry.TrimEnd("\")
    if ((Test-Path -LiteralPath $normalized) -and (@($env:Path -split ";" | Where-Object { $_ }) -notcontains $normalized)) {
        $env:Path = "$normalized;$env:Path"
    }
}

function Invoke-Step {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = (Get-Location).Path
    )

    try {
        Push-Location -LiteralPath $WorkingDirectory
        $output = & $FilePath @Arguments 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
        [pscustomobject]@{
            name = $Name
            command = ($FilePath + " " + ($Arguments -join " ")).Trim()
            workingDirectory = $WorkingDirectory
            success = ($exitCode -eq 0)
            exitCode = $exitCode
            output = $output.Trim()
        }
    } catch {
        [pscustomobject]@{
            name = $Name
            command = ($FilePath + " " + ($Arguments -join " ")).Trim()
            workingDirectory = $WorkingDirectory
            success = $false
            exitCode = $null
            output = $_.Exception.Message
        }
    } finally {
        Pop-Location
    }
}

Add-PathCandidate -PathEntry $NodeRoot
Add-PathCandidate -PathEntry $PyScripts
Add-PathCandidate -PathEntry $LocalBin

if (-not $RepoRoot) {
    $probe = & $ProbeScript | ConvertFrom-Json
    $RepoRoot = $probe.repoRoot
}

if (-not $RepoRoot) {
    [pscustomobject]@{
        repoDependencyInstallResult = "NOT_EXECUTED"
        repoRoot = $null
        exactBlocker = "REPO_PATH_NOT_VISIBLE_FROM_B_MACHINE"
        nextAction = "Expose the repo root to B machine through a shared path or mapped drive, then rerun the bootstrap."
    } | ConvertTo-Json -Depth 6
    return
}

$agents = @()
if (Test-Path -LiteralPath (Join-Path $RepoRoot "AGENTS.md")) {
    $agents += (Join-Path $RepoRoot "AGENTS.md")
}
foreach ($workspace in @("agent-kernel", "bzclaw-console-prototype", "bzclaw-frontend", "bzclaw-test")) {
    $workspaceRoot = Join-Path $RepoRoot $workspace
    $workspaceAgent = Join-Path $workspaceRoot "AGENTS.md"
    if (Test-Path -LiteralPath $workspaceAgent) {
        $agents += $workspaceAgent
    }
}

$steps = @()
$stepPlan = @(
    @{ Name = "pnpm install agent-kernel"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "agent-kernel"), "install", "--frozen-lockfile"); WorkingDirectory = $RepoRoot },
    @{ Name = "pnpm install bzclaw-console-prototype"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "bzclaw-console-prototype"), "install", "--frozen-lockfile"); WorkingDirectory = $RepoRoot },
    @{ Name = "pnpm install bzclaw-frontend"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "bzclaw-frontend"), "install", "--frozen-lockfile"); WorkingDirectory = $RepoRoot },
    @{ Name = "pnpm install bzclaw-test"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "bzclaw-test"), "install", "--frozen-lockfile"); WorkingDirectory = $RepoRoot },
    @{ Name = "uv sync"; FilePath = "uv"; Arguments = @("sync", "--frozen", "--group", "contract-sync", "--group", "dev", "--no-default-groups"); WorkingDirectory = $RepoRoot },
    @{ Name = "playwright install in bzclaw-console-prototype"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "bzclaw-console-prototype"), "exec", "playwright", "install"); WorkingDirectory = $RepoRoot }
)

$firstFailure = $null
foreach ($plannedStep in $stepPlan) {
    if ($firstFailure) {
        $steps += [pscustomobject]@{
            name = $plannedStep.Name
            command = ($plannedStep.FilePath + " " + ($plannedStep.Arguments -join " ")).Trim()
            workingDirectory = $plannedStep.WorkingDirectory
            success = $false
            exitCode = $null
            output = "NOT_RUN_BECAUSE_PREVIOUS_STEP_FAILED"
        }
        continue
    }

    $result = Invoke-Step -Name $plannedStep.Name -FilePath $plannedStep.FilePath -Arguments $plannedStep.Arguments -WorkingDirectory $plannedStep.WorkingDirectory
    $steps += $result
    if (-not $result.success) {
        $firstFailure = $result
    }
}

[pscustomobject]@{
    repoDependencyInstallResult = if ($firstFailure) { "FAILED" } else { "SUCCESS" }
    repoRoot = $RepoRoot
    agentsInScope = $agents
    steps = $steps
    exactBlocker = if ($firstFailure) { $firstFailure.output } else { $null }
} | ConvertTo-Json -Depth 8
