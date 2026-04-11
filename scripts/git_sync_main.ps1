param(
    [string]$CommitMessage = "",
    [switch]$StageAll
)

& (Join-Path $PSScriptRoot "git_sync_bside_main.ps1") -CommitMessage $CommitMessage -StageAll:$StageAll
exit $LASTEXITCODE
