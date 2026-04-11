$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillDir = Split-Path -Parent $ScriptDir
$RootDir = Split-Path -Parent $SkillDir
python "$SkillDir\scripts\run_semantic_filter.py" --root "$RootDir" @args
