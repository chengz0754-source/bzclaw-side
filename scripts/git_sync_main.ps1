param(
    [string]$CommitMessage = "",
    [switch]$StageAll
)

Write-Warning "git_sync_main.ps1 is deprecated. Use .\scripts\git_sync_repo_main.ps1 instead."
& (Join-Path $PSScriptRoot "git_sync_repo_main.ps1") -CommitMessage $CommitMessage -StageAll:$StageAll
exit $LASTEXITCODE
