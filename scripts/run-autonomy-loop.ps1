param(
    [string]$PythonExe = "python",
    [string]$OutputDir = "runtime_logs/autonomy"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$qualityGatePath = Join-Path $OutputDir "quality-gate.json"
$agentPacketPath = Join-Path $OutputDir "agent-packet.json"
$handoffBriefPath = Join-Path $OutputDir "handoff-brief.md"

& $PythonExe -m roxauto quality-gate --output $qualityGatePath
$qualityExitCode = $LASTEXITCODE

& $PythonExe -m roxauto agent-packet --quality-gate $qualityGatePath --output $agentPacketPath
& $PythonExe -m roxauto handoff-brief --quality-gate $qualityGatePath --agent-packet $agentPacketPath --output $handoffBriefPath

Write-Host "quality gate: $qualityGatePath"
Write-Host "agent packet: $agentPacketPath"
Write-Host "handoff brief: $handoffBriefPath"
Write-Host "next step: rely on Codex automatic GitHub review or mention @codex review on the PR."

exit $qualityExitCode
