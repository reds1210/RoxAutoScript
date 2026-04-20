param(
    [Parameter(Mandatory = $true)]
    [string]$Track,

    [string]$BaseBranch = "main",

    [string]$ParentDir = ".."
)

$ErrorActionPreference = "Stop"

$sanitized = $Track -replace "/", "-"
$worktreePath = Join-Path $ParentDir ("RoxAutoScript-wt-" + ($sanitized -replace "^codex-", ""))

Write-Host "Track: $Track"
Write-Host "Base branch: $BaseBranch"
Write-Host "Worktree path: $worktreePath"

$branchExists = $false
git show-ref --verify --quiet ("refs/heads/" + $Track)
if ($LASTEXITCODE -eq 0) {
    $branchExists = $true
}

if (Test-Path $worktreePath) {
    throw "Worktree path already exists: $worktreePath"
}

if ($branchExists) {
    git worktree add $worktreePath $Track
}
else {
    git worktree add $worktreePath -b $Track $BaseBranch
}

Write-Host "Worktree created."

