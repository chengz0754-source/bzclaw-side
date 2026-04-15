[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$env:NODE_OPTIONS = "--dns-result-order=ipv4first"
$env:NODE_NO_WARNINGS = "1"

$NodeRoot = Join-Path $env:LOCALAPPDATA "BZCLAWToolchain\node\current"
$PyScripts = Join-Path $env:APPDATA "Python\Python312\Scripts"
$LocalBin = Join-Path $env:USERPROFILE ".local\bin"
$WorkspaceNames = @("agent-kernel", "bzclaw-console-prototype", "bzclaw-frontend", "bzclaw-test")

function Add-PathCandidate {
    param([string]$PathEntry)

    if ([string]::IsNullOrWhiteSpace($PathEntry)) {
        return
    }

    $normalized = $PathEntry.TrimEnd("\")
    if (-not (Test-Path -LiteralPath $normalized)) {
        return
    }

    $entries = @($env:Path -split ";" | Where-Object { $_ })
    if ($entries -notcontains $normalized) {
        $env:Path = "$normalized;$env:Path"
    }
}

function Invoke-Probe {
    param(
        [string]$Name,
        [string]$Command,
        [string[]]$Arguments = @()
    )

    try {
        $output = & $Command @Arguments 2>&1 | Out-String
        [pscustomobject]@{
            name = $Name
            command = ($Command + " " + ($Arguments -join " ")).Trim()
            success = ($LASTEXITCODE -eq 0)
            exitCode = $LASTEXITCODE
            output = $output.Trim()
        }
    } catch {
        [pscustomobject]@{
            name = $Name
            command = ($Command + " " + ($Arguments -join " ")).Trim()
            success = $false
            exitCode = $null
            output = $_.Exception.Message
        }
    }
}

function Test-WorkspaceRoot {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }

    foreach ($workspace in $WorkspaceNames) {
        if (-not (Test-Path -LiteralPath (Join-Path $Path $workspace))) {
            return $false
        }
    }

    return $true
}

function Get-DirectCandidates {
    $drives = Get-PSDrive -PSProvider FileSystem
    $candidates = @(
        "E:\bzclaw",
        "D:\bzclaw",
        "C:\bzclaw",
        "F:\bzclaw"
    )

    foreach ($drive in $drives) {
        $root = $drive.Root.TrimEnd("\")
        foreach ($parent in @("", "repos", "src", "shared", "workspace", "workspaces", "projects", "code", "repo")) {
            if ([string]::IsNullOrWhiteSpace($parent)) {
                $candidates += "$root\bzclaw"
            } else {
                $candidates += "$root\$parent\bzclaw"
            }
        }

        if ($drive.DisplayRoot) {
            $displayRoot = $drive.DisplayRoot.TrimEnd("\")
            foreach ($parent in @("", "repos", "src", "shared", "workspace", "workspaces", "projects", "code", "repo")) {
                if ([string]::IsNullOrWhiteSpace($parent)) {
                    $candidates += "$displayRoot\bzclaw"
                } else {
                    $candidates += "$displayRoot\$parent\bzclaw"
                }
            }
        }
    }

    $candidates | Select-Object -Unique
}

function Get-RootNamedDirectories {
    $results = @()
    foreach ($drive in Get-PSDrive -PSProvider FileSystem) {
        $root = $drive.Root
        if (-not (Test-Path -LiteralPath $root)) {
            continue
        }

        $matches = Get-ChildItem -LiteralPath $root -Directory -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "*bzclaw*" }

        foreach ($match in $matches) {
            $results += [pscustomobject]@{
                path = $match.FullName
                hasGit = (Test-Path -LiteralPath (Join-Path $match.FullName ".git"))
                hasAllWorkspaces = (Test-WorkspaceRoot -Path $match.FullName)
            }
        }
    }

    $results
}

function Get-WorkspaceHits {
    $hits = @()
    foreach ($drive in Get-PSDrive -PSProvider FileSystem) {
        $root = $drive.Root
        if (-not (Test-Path -LiteralPath $root)) {
            continue
        }

        foreach ($workspace in $WorkspaceNames) {
            $matches = Get-ChildItem -LiteralPath $root -Directory -Recurse -Depth 4 -Filter $workspace -Force -ErrorAction SilentlyContinue
            foreach ($match in $matches) {
                if ($match.FullName -like "*`$RECYCLE.BIN*") {
                    continue
                }
                if ($match.FullName -like "*System Volume Information*") {
                    continue
                }

                $hits += [pscustomobject]@{
                    workspace = $workspace
                    path = $match.FullName
                    parent = Split-Path -Parent $match.FullName
                }
            }
        }
    }

    $hits
}

function Resolve-RepoRoot {
    $directCandidates = Get-DirectCandidates
    foreach ($candidate in $directCandidates) {
        if (Test-WorkspaceRoot -Path $candidate) {
            return [pscustomobject]@{
                path = (Resolve-Path -LiteralPath $candidate).Path
                source = "direct_candidate"
            }
        }
    }

    $rootNamedDirectories = Get-RootNamedDirectories
    foreach ($entry in $rootNamedDirectories) {
        if ($entry.hasAllWorkspaces) {
            return [pscustomobject]@{
                path = $entry.path
                source = "root_named_directory"
            }
        }
    }

    $workspaceHits = @(Get-WorkspaceHits)
    if (@($workspaceHits).Count -gt 0) {
        foreach ($candidateParent in ($workspaceHits | Select-Object -ExpandProperty parent -Unique)) {
            if (Test-WorkspaceRoot -Path $candidateParent) {
                return [pscustomobject]@{
                    path = $candidateParent
                    source = "workspace_search"
                }
            }
        }
    }

    return [pscustomobject]@{
        path = $null
        source = $null
        directCandidates = $directCandidates
        rootNamedDirectories = $rootNamedDirectories
        workspaceHits = $workspaceHits
    }
}

Add-PathCandidate -PathEntry $NodeRoot
Add-PathCandidate -PathEntry $PyScripts
Add-PathCandidate -PathEntry $LocalBin

$machineProbes = @(
    Invoke-Probe -Name "node" -Command "node" -Arguments @("-v")
    Invoke-Probe -Name "pnpm" -Command "pnpm" -Arguments @("-v")
    Invoke-Probe -Name "python312" -Command "py" -Arguments @("-3.12", "--version")
    Invoke-Probe -Name "uv" -Command "uv" -Arguments @("--version")
    Invoke-Probe -Name "ruff" -Command "ruff" -Arguments @("--version")
    Invoke-Probe -Name "corepack" -Command "corepack" -Arguments @("--version")
)

$networkMappings = net use | Out-String
$repoResolution = Resolve-RepoRoot

[pscustomobject]@{
    generatedAt = (Get-Date).ToString("s")
    toolPathsInjected = @($NodeRoot, $PyScripts, $LocalBin)
    machineProbes = $machineProbes
    psDrives = @(Get-PSDrive -PSProvider FileSystem | Select-Object Name, Root, DisplayRoot)
    networkMappings = $networkMappings.Trim()
    repoPathVisibleOnBMachine = if ($repoResolution.path) { "YES" } else { "NO" }
    repoRoot = $repoResolution.path
    repoResolutionSource = $repoResolution.source
    directCandidatesChecked = @($repoResolution.directCandidates)
    rootNamedDirectories = @($repoResolution.rootNamedDirectories)
    workspaceHits = @($repoResolution.workspaceHits)
    exactBlocker = if ($repoResolution.path) { $null } else { "REPO_PATH_NOT_VISIBLE_FROM_B_MACHINE" }
    nextAction = if ($repoResolution.path) { "Proceed with repo dependency bootstrap." } else { "Expose the repo root to B machine through a shared path or mapped drive, then rerun this prompt." }
} | ConvertTo-Json -Depth 8
