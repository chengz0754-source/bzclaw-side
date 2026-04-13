$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillDir = Split-Path -Parent $ScriptDir
$RootDir = Split-Path -Parent $SkillDir
python "$SkillDir\scripts\run_market_route_pipeline.py" --root "$RootDir" @args
