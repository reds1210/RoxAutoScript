param(
    [string]$Track,
    [string]$BaseBranch = "main",
    [string]$ParentDir = "..",
    [switch]$AllowLegacyWorktree
)

$ErrorActionPreference = "Stop"

if (-not $AllowLegacyWorktree) {
    Write-Warning "scripts/new-worktree.ps1 is a legacy helper. The repo now defaults to one local working directory with branch-first delivery."
    Write-Host "Branch-first quick start:"
    Write-Host "  git status"
    Write-Host "  git switch main"
    Write-Host "  git pull --ff-only"
    Write-Host "  git switch -c codex/<branch-name>"
    Write-Host ""
    Write-Host "If you truly need the retired worktree flow, rerun this script with -AllowLegacyWorktree."
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Track)) {
    throw "Track is required when -AllowLegacyWorktree is used."
}

$sanitized = $Track -replace "/", "-"
$worktreePath = Join-Path $ParentDir ("RoxAutoScript-wt-" + ($sanitized -replace "^codex-", ""))

Write-Warning "Running legacy worktree creation flow."
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

Write-Host "Legacy worktree created."
