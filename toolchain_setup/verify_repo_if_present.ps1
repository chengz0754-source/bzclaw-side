[CmdletBinding()]
param(
    [string]$RepoRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$env:NODE_OPTIONS = "--dns-result-order=ipv4first"
$env:NODE_NO_WARNINGS = "1"

$PersistentToolRoot = Join-Path $env:LOCALAPPDATA "BZCLAWToolchain"
$NodeCurrentDir = Join-Path $PersistentToolRoot "node\current"
$PnpmCmd = Join-Path $NodeCurrentDir "pnpm.cmd"
$PythonUserBase = (& py -3.12 -c "import site; print(site.USER_BASE)").Trim()
$PythonUserScripts = Join-Path $PythonUserBase "Python312\Scripts"
$LocalBin = Join-Path $env:USERPROFILE ".local\bin"

function Add-PathCandidate {
    param([string]$PathEntry)
    if ([string]::IsNullOrWhiteSpace($PathEntry)) {
        return
    }
    $normalized = $PathEntry.TrimEnd("\")
    if (Test-Path -LiteralPath $normalized) {
        $entries = @($env:Path -split ";" | Where-Object { $_ })
        if ($entries -notcontains $normalized) {
            $env:Path = "$normalized;$env:Path"
        }
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
            exitCode = $exitCode
            success = ($exitCode -eq 0)
            output = $output.Trim()
        }
    } catch {
        [pscustomobject]@{
            name = $Name
            command = ($FilePath + " " + ($Arguments -join " ")).Trim()
            workingDirectory = $WorkingDirectory
            exitCode = $null
            success = $false
            output = $_.Exception.Message
        }
    } finally {
        Pop-Location
    }
}

function Resolve-RepoRoot {
    param([string]$Candidate)

    if ($Candidate -and (Test-Path -LiteralPath $Candidate)) {
        return (Resolve-Path -LiteralPath $Candidate).Path
    }

    $commonCandidates = @()
    foreach ($drive in (Get-PSDrive -PSProvider FileSystem)) {
        $commonCandidates += (Join-Path $drive.Root "bzclaw")
        $commonCandidates += (Join-Path $drive.Root "repos\bzclaw")
        $commonCandidates += (Join-Path $drive.Root "src\bzclaw")
    }

    foreach ($path in $commonCandidates | Select-Object -Unique) {
        if (Test-Path -LiteralPath $path) {
            return (Resolve-Path -LiteralPath $path).Path
        }
    }

    return $null
}

Add-PathCandidate -PathEntry $NodeCurrentDir
Add-PathCandidate -PathEntry $PythonUserScripts
Add-PathCandidate -PathEntry $LocalBin

$resolvedRepoRoot = Resolve-RepoRoot -Candidate $RepoRoot
if (-not $resolvedRepoRoot) {
    [pscustomobject]@{
        repoPathVisibleOnBMachine = "NO"
        repoRoot = $null
        repoValidationDeferredBecauseRepoIsNotPresentOnBMachine = $true
        repoLevelValidation = "DEFERRED"
        reason = "REPO_IS_NOT_PRESENT_ON_B_MACHINE"
    } | ConvertTo-Json -Depth 6
    return
}

$workspaceMap = [ordered]@{
    agentKernel = Join-Path $resolvedRepoRoot "agent-kernel"
    consolePrototype = Join-Path $resolvedRepoRoot "bzclaw-console-prototype"
    frontend = Join-Path $resolvedRepoRoot "bzclaw-frontend"
    testWorkspace = Join-Path $resolvedRepoRoot "bzclaw-test"
}

$workspaceStatus = foreach ($entry in $workspaceMap.GetEnumerator()) {
    [pscustomobject]@{
        name = $entry.Key
        path = $entry.Value
        exists = (Test-Path -LiteralPath $entry.Value)
    }
}

$requiredMissing = @($workspaceStatus | Where-Object { -not $_.exists })
if ($requiredMissing.Count -gt 0) {
    [pscustomobject]@{
        repoPathVisibleOnBMachine = "YES"
        repoRoot = $resolvedRepoRoot
        repoLevelValidation = "BLOCKED"
        workspaceStatus = $workspaceStatus
        blocker = "Required repo workspaces are missing."
    } | ConvertTo-Json -Depth 6
    return
}

$steps = @(
    Invoke-Step -Name "pnpm install agent-kernel" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.agentKernel, "install", "--frozen-lockfile")
    Invoke-Step -Name "pnpm install bzclaw-console-prototype" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.consolePrototype, "install", "--frozen-lockfile")
    Invoke-Step -Name "pnpm install bzclaw-frontend" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.frontend, "install", "--frozen-lockfile")
    Invoke-Step -Name "pnpm install bzclaw-test" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.testWorkspace, "install", "--frozen-lockfile")
    Invoke-Step -Name "uv sync" -FilePath "uv" -Arguments @("sync", "--frozen", "--group", "contract-sync", "--group", "dev", "--no-default-groups") -WorkingDirectory $resolvedRepoRoot
    Invoke-Step -Name "playwright install in console prototype" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.consolePrototype, "exec", "playwright", "install")
    Invoke-Step -Name "uv run ruff --version" -FilePath "uv" -Arguments @("run", "ruff", "--version") -WorkingDirectory $resolvedRepoRoot
    Invoke-Step -Name "uv run mypy tools/shared_contracts.py" -FilePath "uv" -Arguments @("run", "mypy", "tools/shared_contracts.py") -WorkingDirectory $resolvedRepoRoot
    Invoke-Step -Name "uv run python -m pytest tools/tests -q" -FilePath "uv" -Arguments @("run", "python", "-m", "pytest", "tools/tests", "-q") -WorkingDirectory $resolvedRepoRoot
    Invoke-Step -Name "contracts:check:pydantic-ts" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.frontend, "run", "contracts:check:pydantic-ts")
    Invoke-Step -Name "smoke:list" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.consolePrototype, "run", "smoke:list")
    Invoke-Step -Name "smoke" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.consolePrototype, "run", "smoke")
    Invoke-Step -Name "smoke:evidence" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.consolePrototype, "run", "smoke:evidence")
    Invoke-Step -Name "test:robot" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.testWorkspace, "run", "test:robot")
    Invoke-Step -Name "test:orchestrate" -FilePath $PnpmCmd -Arguments @("-C", $workspaceMap.testWorkspace, "run", "test:orchestrate")
)

[pscustomobject]@{
    repoPathVisibleOnBMachine = "YES"
    repoRoot = $resolvedRepoRoot
    repoLevelValidation = "ATTEMPTED"
    workspaceStatus = $workspaceStatus
    steps = $steps
} | ConvertTo-Json -Depth 8
