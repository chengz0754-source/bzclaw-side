[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$env:NODE_OPTIONS = "--dns-result-order=ipv4first"
$env:NODE_NO_WARNINGS = "1"

$currentUserExecutionPolicy = Get-ExecutionPolicy -Scope CurrentUser
if ($currentUserExecutionPolicy -eq "Undefined") {
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
}

$ControlRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$DownloadsRoot = Join-Path $ControlRoot "downloads"
$PersistentToolRoot = Join-Path $env:LOCALAPPDATA "BZCLAWToolchain"
$NodeRoot = Join-Path $PersistentToolRoot "node"
$NodeCurrentDir = Join-Path $NodeRoot "current"
$NodeExe = Join-Path $NodeCurrentDir "node.exe"
$CorepackCmd = Join-Path $NodeCurrentDir "corepack.cmd"
$PnpmCmd = Join-Path $NodeCurrentDir "pnpm.cmd"
$PythonUserBase = (& py -3.12 -c "import site; print(site.USER_BASE)").Trim()
$PythonUserScripts = Join-Path $PythonUserBase "Python312\Scripts"
$UvExe = Join-Path $PythonUserScripts "uv.exe"
$LocalBin = Join-Path $env:USERPROFILE ".local\bin"
$PlaywrightCache = Join-Path $env:LOCALAPPDATA "ms-playwright"

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "== $Message =="
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Add-PathEntry {
    param(
        [string]$PathEntry,
        [switch]$PersistToUser
    )

    if ([string]::IsNullOrWhiteSpace($PathEntry)) {
        return
    }

    $normalized = $PathEntry.TrimEnd("\")
    $processEntries = @($env:Path -split ";" | Where-Object { $_ })
    if ($processEntries -notcontains $normalized) {
        $env:Path = "$normalized;$env:Path"
    }

    if ($PersistToUser) {
        $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $userEntries = @()
        if ($userPath) {
            $userEntries = @($userPath -split ";" | Where-Object { $_ })
        }

        if ($userEntries -notcontains $normalized) {
            $newUserPath = (@($normalized) + $userEntries | Select-Object -Unique) -join ";"
            [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
        }
    }
}

function Invoke-Checked {
    param(
        [string]$Label,
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    Write-Host "$Label -> $FilePath $($Arguments -join ' ')"
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

function Get-Node24Release {
    $content = Invoke-RestMethod "https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt"
    $lines = @($content -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $match = $lines | Where-Object { $_ -match "node-v(?<version>24\.[0-9.]+)-win-x64\.zip$" } | Select-Object -First 1
    if (-not $match) {
        throw "Unable to resolve a latest-v24.x Windows x64 Node release."
    }

    $fileName = ($match -split "\s+")[-1]
    $version = [regex]::Match($fileName, "node-v(?<version>24\.[0-9.]+)-win-x64\.zip").Groups["version"].Value
    if (-not $version) {
        throw "Unable to parse Node version from $fileName."
    }

    [pscustomobject]@{
        Version = $version
        FileName = $fileName
        Uri = "https://nodejs.org/dist/latest-v24.x/$fileName"
    }
}

Ensure-Directory -Path $ControlRoot
Ensure-Directory -Path $DownloadsRoot
Ensure-Directory -Path $PersistentToolRoot
Ensure-Directory -Path $NodeRoot

Write-Section "Verify Python 3.12"
Invoke-Checked -Label "Python 3.12" -FilePath "py" -Arguments @("-3.12", "--version")

Write-Section "Install Node.js >= 24"
$nodeRelease = Get-Node24Release
$nodeZip = Join-Path $DownloadsRoot $nodeRelease.FileName
$nodeExtractRoot = Join-Path $DownloadsRoot "node-extract"
if (-not (Test-Path -LiteralPath $nodeZip)) {
    Invoke-WebRequest -Uri $nodeRelease.Uri -OutFile $nodeZip
}
if (Test-Path -LiteralPath $nodeExtractRoot) {
    Remove-Item -LiteralPath $nodeExtractRoot -Recurse -Force
}
Ensure-Directory -Path $nodeExtractRoot
Expand-Archive -LiteralPath $nodeZip -DestinationPath $nodeExtractRoot -Force
$extractedNodeDir = Join-Path $nodeExtractRoot ("node-v{0}-win-x64" -f $nodeRelease.Version)
if (-not (Test-Path -LiteralPath $extractedNodeDir)) {
    throw "Extracted Node directory not found at $extractedNodeDir."
}
if (Test-Path -LiteralPath $NodeCurrentDir) {
    Remove-Item -LiteralPath $NodeCurrentDir -Recurse -Force
}
Move-Item -LiteralPath $extractedNodeDir -Destination $NodeCurrentDir
Add-PathEntry -PathEntry $NodeCurrentDir -PersistToUser
Invoke-Checked -Label "Node.js" -FilePath $NodeExe -Arguments @("-v")

Write-Section "Enable corepack and activate pnpm@9.15.0"
Invoke-Checked -Label "corepack enable" -FilePath $CorepackCmd -Arguments @("enable")
Invoke-Checked -Label "corepack prepare pnpm@9.15.0" -FilePath $CorepackCmd -Arguments @("prepare", "pnpm@9.15.0", "--activate")
Invoke-Checked -Label "pnpm version" -FilePath $PnpmCmd -Arguments @("-v")

Write-Section "Install uv into the Python 3.12 user environment"
Invoke-Checked -Label "pip install uv" -FilePath "py" -Arguments @("-3.12", "-m", "pip", "install", "--user", "--upgrade", "uv")
Add-PathEntry -PathEntry $PythonUserScripts -PersistToUser
Invoke-Checked -Label "uv version" -FilePath $UvExe -Arguments @("--version")

Write-Section "Install or upgrade ruff via uv tool"
$toolList = ""
try {
    $toolList = & $UvExe tool list 2>$null | Out-String
} catch {
    $toolList = ""
}
if ($toolList -match "(?m)^ruff\b") {
    Invoke-Checked -Label "uv tool upgrade ruff" -FilePath $UvExe -Arguments @("tool", "upgrade", "ruff")
} else {
    Invoke-Checked -Label "uv tool install ruff@latest" -FilePath $UvExe -Arguments @("tool", "install", "ruff@latest")
}
Add-PathEntry -PathEntry $LocalBin -PersistToUser
Invoke-Checked -Label "ruff version" -FilePath (Join-Path $LocalBin "ruff.exe") -Arguments @("--version")

Write-Section "Install Playwright runtime"
Add-PathEntry -PathEntry $NodeCurrentDir
Invoke-Checked -Label "Playwright CLI version" -FilePath $PnpmCmd -Arguments @("dlx", "playwright@latest", "--version")
Invoke-Checked -Label "Playwright browser install" -FilePath $PnpmCmd -Arguments @("dlx", "playwright@latest", "install")
if (-not (Test-Path -LiteralPath $PlaywrightCache)) {
    throw "Playwright cache directory was not created at $PlaywrightCache."
}

Write-Section "Installation summary"
$summary = [pscustomobject]@{
    node = (& $NodeExe -v).Trim()
    pnpm = (& $PnpmCmd -v).Trim()
    python = (& py -3.12 --version).Trim()
    uv = (& $UvExe --version).Trim()
    ruff = (& (Join-Path $LocalBin "ruff.exe") --version).Trim()
    playwrightVersion = (& $PnpmCmd dlx playwright@latest --version).Trim()
    playwrightCache = $PlaywrightCache
}
$summary | ConvertTo-Json -Depth 4
