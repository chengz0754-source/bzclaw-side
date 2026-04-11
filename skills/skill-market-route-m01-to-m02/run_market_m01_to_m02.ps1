param(
    [string]$InputDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutputDir = (Join-Path $PSScriptRoot "outputs"),
    [string]$Glob = "Market-research*.xlsx",
    [switch]$Overwrite,
    [switch]$Debug
)

$arguments = @(
    (Join-Path $PSScriptRoot "run_market_m01_to_m02.py"),
    "--input-dir", $InputDir,
    "--output-dir", $OutputDir,
    "--glob", $Glob
)

if ($Overwrite) {
    $arguments += "--overwrite"
}

if ($Debug) {
    $arguments += "--debug"
}

& python @arguments
exit $LASTEXITCODE
