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
        repoValidationResult = "NOT_EXECUTED"
        repoRoot = $null
        exactBlocker = "REPO_PATH_NOT_VISIBLE_FROM_B_MACHINE"
        nextAction = "Expose the repo root to B machine through a shared path or mapped drive, then rerun validation."
    } | ConvertTo-Json -Depth 6
    return
}

$steps = @()
$essentialSteps = @(
    @{ Name = "uv run ruff --version"; FilePath = "uv"; Arguments = @("run", "ruff", "--version"); WorkingDirectory = $RepoRoot },
    @{ Name = "uv run mypy tools/shared_contracts.py"; FilePath = "uv"; Arguments = @("run", "mypy", "tools/shared_contracts.py"); WorkingDirectory = $RepoRoot },
    @{ Name = "uv run python -m pytest tools/tests -q"; FilePath = "uv"; Arguments = @("run", "python", "-m", "pytest", "tools/tests", "-q"); WorkingDirectory = $RepoRoot },
    @{ Name = "contracts:check:pydantic-ts"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "bzclaw-frontend"), "run", "contracts:check:pydantic-ts"); WorkingDirectory = $RepoRoot },
    @{ Name = "smoke:list"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "bzclaw-console-prototype"), "run", "smoke:list"); WorkingDirectory = $RepoRoot }
)

$firstFailure = $null
foreach ($plannedStep in $essentialSteps) {
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

$smokeListSucceeded = $steps | Where-Object { $_.name -eq "smoke:list" -and $_.success }
if ($smokeListSucceeded) {
    foreach ($plannedStep in @(
        @{ Name = "smoke"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "bzclaw-console-prototype"), "run", "smoke"); WorkingDirectory = $RepoRoot },
        @{ Name = "smoke:evidence"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "bzclaw-console-prototype"), "run", "smoke:evidence"); WorkingDirectory = $RepoRoot },
        @{ Name = "test:robot"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "bzclaw-test"), "run", "test:robot"); WorkingDirectory = $RepoRoot },
        @{ Name = "test:orchestrate"; FilePath = $PnpmCmd; Arguments = @("-C", (Join-Path $RepoRoot "bzclaw-test"), "run", "test:orchestrate"); WorkingDirectory = $RepoRoot }
    )) {
        $steps += Invoke-Step -Name $plannedStep.Name -FilePath $plannedStep.FilePath -Arguments $plannedStep.Arguments -WorkingDirectory $plannedStep.WorkingDirectory
    }
}

[pscustomobject]@{
    repoValidationResult = if ($firstFailure) { "FAILED" } else { "SUCCESS" }
    repoRoot = $RepoRoot
    steps = $steps
    exactBlocker = if ($firstFailure) { $firstFailure.output } else { $null }
} | ConvertTo-Json -Depth 8
