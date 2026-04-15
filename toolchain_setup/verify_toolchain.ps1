[CmdletBinding()]
param()

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
$PlaywrightCache = Join-Path $env:LOCALAPPDATA "ms-playwright"

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

function Invoke-Probe {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    try {
        $output = & $FilePath @Arguments 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
        [pscustomobject]@{
            name = $Name
            command = ($FilePath + " " + ($Arguments -join " ")).Trim()
            exitCode = $exitCode
            success = ($exitCode -eq 0)
            output = $output.Trim()
        }
    } catch {
        [pscustomobject]@{
            name = $Name
            command = ($FilePath + " " + ($Arguments -join " ")).Trim()
            exitCode = $null
            success = $false
            output = $_.Exception.Message
        }
    }
}

Add-PathCandidate -PathEntry $NodeCurrentDir
Add-PathCandidate -PathEntry $PythonUserScripts
Add-PathCandidate -PathEntry $LocalBin

$playwrightCacheEntries = @()
if (Test-Path -LiteralPath $PlaywrightCache) {
    $playwrightCacheEntries = @(Get-ChildItem -LiteralPath $PlaywrightCache -Directory | Select-Object -ExpandProperty Name)
}

$results = [pscustomobject]@{
    generatedAt = (Get-Date).ToString("s")
    pathCandidates = [pscustomobject]@{
        node = $NodeCurrentDir
        pythonUserScripts = $PythonUserScripts
        localBin = $LocalBin
        playwrightCache = $PlaywrightCache
    }
    probes = @(
        Invoke-Probe -Name "node" -FilePath "node" -Arguments @("-v")
        Invoke-Probe -Name "pnpm" -FilePath "pnpm" -Arguments @("-v")
        Invoke-Probe -Name "python312" -FilePath "py" -Arguments @("-3.12", "--version")
        Invoke-Probe -Name "uv" -FilePath "uv" -Arguments @("--version")
        Invoke-Probe -Name "ruff" -FilePath "ruff" -Arguments @("--version")
        Invoke-Probe -Name "corepack" -FilePath "corepack" -Arguments @("--version")
        Invoke-Probe -Name "uv tool list" -FilePath "uv" -Arguments @("tool", "list")
        Invoke-Probe -Name "playwright version via pnpm.cmd dlx" -FilePath $PnpmCmd -Arguments @("dlx", "playwright@latest", "--version")
    )
    playwrightCacheEntries = $playwrightCacheEntries
}

$results | ConvertTo-Json -Depth 6
