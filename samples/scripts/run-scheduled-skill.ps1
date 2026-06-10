#Requires -Version 5.1
<#
.SYNOPSIS
  Headless launcher for Claude Code scheduled-task SKILL.md files.

.DESCRIPTION
  Reads a SKILL.md from `~/.claude/scheduled-tasks/<Skill>/` and pipes it as
  the prompt to `claude --print`, with `<workspace>` on the tool-access list.
  Output is tee'd to `<workspace>\tasks\scheduled-logs\<Skill>_<date-time>.log`.

  Invoked by Windows Task Scheduler entries that own the cron cadence. This
  is the workaround for the built-in `scheduled-tasks` MCP being unconnected
  in this environment — registration there would be the canonical path, but
  until it's available, Task Scheduler + this wrapper is the durable route.

  Token Budget additions (2026-06-10):
  - A Stage-0 preflight gate for the heartbeat skill: a deterministic Python
    check decides whether the fire needs the LLM at all (exit 100 = skip).
    Most low-duty-cycle fires end here at zero model cost.
  - A per-skill model map: scheduled work runs a mid-tier model; frontier
    models stay interactive-only.
  - A per-cycle dollar budget (`--max-budget-usd`) and a capped thinking
    budget (`MAX_THINKING_TOKENS`) — thinking bills as output tokens.

.PARAMETER Skill
  Name of the subfolder under `~/.claude/scheduled-tasks/` (e.g. `morning-brief`).

.PARAMETER DryRun
  Resolve + print paths, dispatch decision, and prompt size; do not invoke
  `claude` or the gate's scans.

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File run-scheduled-skill.ps1 -Skill morning-brief
#>
param(
    [Parameter(Mandatory)][string]$Skill,
    [switch]$DryRun
)

# Native-command hygiene: do NOT set $ErrorActionPreference = 'Stop' globally
# (PS 5.1 promotes native stderr to NativeCommandError).
$ErrorActionPreference = 'Continue'

$SkillFile = Join-Path $env:USERPROFILE ".claude\scheduled-tasks\$Skill\SKILL.md"
if (-not (Test-Path $SkillFile)) {
    Write-Error "Skill not found: $SkillFile"
    exit 1
}

$TodayTag = Get-Date -Format 'yyyy-MM-dd-HHmm'
$LogDir = '<workspace>\tasks\scheduled-logs'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "${Skill}_${TodayTag}.log"

if ($DryRun) {
    $prompt = Get-Content $SkillFile -Raw
    Write-Host "Skill:        $Skill"
    Write-Host "SKILL.md:     $SkillFile"
    Write-Host "Log file:     $LogFile"
    Write-Host "Prompt chars: $($prompt.Length)"
    Write-Host "Would invoke: claude --print --permission-mode acceptEdits --max-budget-usd <2|5> [--model sonnet per ModelMap] --add-dir <workspace>"
    if ($Skill -eq 'heartbeat-monitor') {
        Write-Host "Gate:         preflight_gate.py runs first (exit 100 = skip the LLM entirely)"
    }
    exit 0
}

Set-Location '<workspace>'

$prompt = Get-Content $SkillFile -Raw

# --- Stage-0 gate, heartbeat only (gate-don't-loop, 2026-06-10) ------------
# preflight_gate.py decides whether this fire needs the LLM at all:
#   exit 100 -> SKIP (watched files unchanged + deterministic scans pass
#               + an agent cycle ran <24h ago). Log a skip and exit; the
#               "HEARTBEAT_OK (gated skip)" line keeps the dead-man's-switch
#               substring sentinel satisfied.
#   exit 0   -> RUN, with the gate's PREFLIGHT block appended to the prompt
#               so the agent doesn't re-run the scans.
#   other    -> gate bug. FAIL OPEN and run the agent - a broken gate must
#               never silence the heartbeat.
# ASCII only inside strings: PS 5.1 reads a BOM-less file as ANSI, and a
# UTF-8 em-dash decodes to a smart-quote byte that TERMINATES a double-
# quoted string mid-line.
if ($Skill -eq 'heartbeat-monitor') {
    $gateLines = & python '<workspace>\scripts\heartbeat\preflight_gate.py' 2>&1
    $gateExit = $LASTEXITCODE
    if ($null -eq $gateExit) { $gateExit = 0 }
    $gateLines | Tee-Object -FilePath $LogFile -Append | Out-Null
    if ($gateExit -eq 100) {
        Add-Content -Path $LogFile -Value 'HEARTBEAT_SKIP - gate: inputs unchanged, scans pass, agent cycle <24h old' -Encoding utf8
        Add-Content -Path $LogFile -Value 'HEARTBEAT_OK (gated skip - no agent invoked)' -Encoding utf8
        exit 0
    }
    elseif ($gateExit -eq 0) {
        $prompt = $prompt + "`n`n" + (($gateLines | ForEach-Object { "$_" }) -join "`n")
    }
    else {
        Add-Content -Path $LogFile -Value "WARN: preflight gate errored (exit $gateExit) - failing open" -Encoding utf8
    }
}

# --- Model + budget per skill (Token Budget re-tier, 2026-06-10) -----------
# Scheduled headless work runs a mid-tier model; frontier models stay
# interactive/escalation-only. The heartbeat's runaway belt is tighter
# because a gated cycle should be small.
$ModelMap = @{
    'heartbeat-monitor'  = 'sonnet'
    'morning-brief'      = 'sonnet'
    'consolidate-memory' = 'sonnet'
}
$budget = if ($Skill -eq 'heartbeat-monitor') { 2 } else { 5 }
$claudeArgs = @('--print', '--permission-mode', 'acceptEdits', '--max-budget-usd', "$budget")
if ($ModelMap.ContainsKey($Skill)) { $claudeArgs += @('--model', $ModelMap[$Skill]) }
$claudeArgs += @('--add-dir', '<workspace>')
# Cap extended thinking on unattended runs (it bills as output tokens).
$env:MAX_THINKING_TOKENS = '8000'

# Pipe SKILL.md content as stdin; tee all output (stdout + stderr merged) to log.
$cycleLines = $prompt | & claude @claudeArgs *>&1 | Tee-Object -FilePath $LogFile -Append

$code = $LASTEXITCODE
if ($null -eq $code) { $code = 0 }

# Post-cycle: stamp the gate AFTER a clean heartbeat agent cycle so the next
# fire's hash comparison uses post-edit file state (the agent itself writes
# to the watched files mid-cycle).
if ($Skill -eq 'heartbeat-monitor') {
    $hasSentinel = $false
    foreach ($line in $cycleLines) {
        if ("$line" -match 'HEARTBEAT_OK') { $hasSentinel = $true; break }
    }
    if ($hasSentinel) {
        & python '<workspace>\scripts\heartbeat\preflight_gate.py' --mark-cycle 2>&1 |
            Tee-Object -FilePath $LogFile -Append | Out-Null
    }
}

Write-Host "claude exit code: $code"
exit $code
