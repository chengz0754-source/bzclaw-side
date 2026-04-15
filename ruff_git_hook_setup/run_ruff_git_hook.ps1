[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("pre-commit", "pre-push")]
    [string]$HookType,
    [string]$RepoPath,
    [string[]]$Files,
    [string]$RemoteName,
    [string]$RemoteUrl
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ZeroObjectId = "0000000000000000000000000000000000000000"
$ExcludePattern = "(^|/)(node_modules|\.next|playwright-report|test-results|\.venv[^/]*|\.pnpm-store)(/|$)"
$UserHome = if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
    $env:USERPROFILE
} elseif (-not [string]::IsNullOrWhiteSpace($env:HOME)) {
    $env:HOME
} else {
    [Environment]::GetFolderPath("UserProfile")
}
$PreCommitExe = if ([string]::IsNullOrWhiteSpace($UserHome)) {
    $null
} else {
    Join-Path $UserHome ".local\bin\pre-commit.exe"
}

function Resolve-RepoRoot {
    param(
        [string]$CandidatePath
    )

    $fallbackRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
    $candidates = New-Object System.Collections.Generic.List[string]

    if (-not [string]::IsNullOrWhiteSpace($CandidatePath)) {
        $candidates.Add($CandidatePath.Trim())
    }
    $candidates.Add($fallbackRoot)

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        $resolvedCandidate = Resolve-Path -LiteralPath $candidate -ErrorAction SilentlyContinue
        if (-not $resolvedCandidate) {
            continue
        }

        $repoRoot = & git -C $resolvedCandidate.Path rev-parse --show-toplevel 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($repoRoot | Out-String).Trim())) {
            return (Resolve-Path -LiteralPath (($repoRoot | Out-String).Trim())).Path
        }
    }

    throw "Unable to resolve repo root from RepoPath='$CandidatePath' or script root '$fallbackRoot'."
}

function Invoke-GitText {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $output = & git -C $RepoPath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        $message = ($output | Out-String).Trim()
        throw "git $($Arguments -join ' ') failed: $message"
    }

    return @($output)
}

$RepoPath = Resolve-RepoRoot -CandidatePath $RepoPath
$ConfigPath = Join-Path $RepoPath ".pre-commit-config.yaml"

function Get-PreCommitCommandPrefix {
    if ($PreCommitExe -and (Test-Path -LiteralPath $PreCommitExe)) {
        return @($PreCommitExe)
    }

    return @("py", "-3.12", "-m", "uv", "run", "--with", "pre-commit", "pre-commit")
}

function Normalize-RepoPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $trimmed = $Path.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        return $null
    }

    if ([System.IO.Path]::IsPathRooted($trimmed)) {
        $resolved = Resolve-Path -LiteralPath $trimmed -ErrorAction SilentlyContinue
        if (-not $resolved) {
            return $null
        }

        $repoUri = [Uri]((Resolve-Path -LiteralPath $RepoPath).Path + [System.IO.Path]::DirectorySeparatorChar)
        $fileUri = [Uri]($resolved.Path)
        if (-not $repoUri.IsBaseOf($fileUri)) {
            return $null
        }

        $relative = $repoUri.MakeRelativeUri($fileUri).ToString()
        return $relative.Replace("%20", " ")
    }

    $normalized = $trimmed.Replace("\", "/")
    if ($normalized.StartsWith("./")) {
        return $normalized.Substring(2)
    }

    return $normalized
}

function Select-PythonFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Paths
    )

    $selected = New-Object System.Collections.Generic.List[string]
    foreach ($path in $Paths) {
        if ($null -eq $path) {
            continue
        }

        $relative = Normalize-RepoPath -Path $path
        if ([string]::IsNullOrWhiteSpace($relative)) {
            continue
        }

        $relative = $relative.Replace("\", "/")
        if ($relative -match $ExcludePattern) {
            continue
        }

        if ($relative -notmatch "\.(py|pyi)$") {
            continue
        }

        $repoFile = Join-Path $RepoPath ($relative -replace "/", [System.IO.Path]::DirectorySeparatorChar)
        if (-not (Test-Path -LiteralPath $repoFile -PathType Leaf)) {
            continue
        }

        $selected.Add($relative)
    }

    return @($selected | Sort-Object -Unique)
}

function Get-StagedPaths {
    return Invoke-GitText -Arguments @("diff", "--cached", "--name-only", "--diff-filter=ACMR")
}

function Get-PushedPathsFromStdin {
    $inputText = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($inputText)) {
        return @()
    }

    $paths = New-Object System.Collections.Generic.List[string]
    foreach ($line in ($inputText -split "(`r`n|`n|`r)")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $parts = $line -split "\s+"
        if ($parts.Count -lt 4) {
            continue
        }

        $localSha = $parts[1]
        $remoteSha = $parts[3]
        if ($localSha -eq $ZeroObjectId) {
            continue
        }

        $gitArgs = if ($remoteSha -eq $ZeroObjectId) {
            @("log", "--format=", "--name-only", "--diff-filter=ACMR", $localSha, "--not", "--remotes")
        } else {
            @("diff", "--name-only", "--diff-filter=ACMR", $remoteSha, $localSha)
        }

        foreach ($path in (Invoke-GitText -Arguments $gitArgs)) {
            $paths.Add($path)
        }
    }

    return @($paths)
}

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Missing pre-commit config: $ConfigPath"
}

$candidateFiles = if ($Files -and $Files.Count -gt 0) {
    @($Files)
} elseif ($HookType -eq "pre-commit") {
    @(Get-StagedPaths)
} else {
    @(Get-PushedPathsFromStdin)
}

$candidateFiles = @($candidateFiles | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($candidateFiles.Count -eq 0) {
    Write-Output "[ruff-$HookType] No candidate files were provided by the hook."
    exit 0
}

$pythonFiles = @(Select-PythonFiles -Paths @($candidateFiles))
if ($pythonFiles.Count -eq 0) {
    Write-Output "[ruff-$HookType] No Python files matched the hook scope."
    exit 0
}

$prefix = @(Get-PreCommitCommandPrefix)
$command = @($prefix + @("run", "ruff-check", "--config", $ConfigPath, "--hook-stage", $HookType, "--files") + $pythonFiles)

Write-Output "[ruff-$HookType] Running Ruff on $($pythonFiles.Count) file(s)."
foreach ($file in $pythonFiles) {
    Write-Output " - $file"
}

Push-Location $RepoPath
try {
    & $command[0] $command[1..($command.Count - 1)]
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
