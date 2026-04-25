param(
    [string]$BaseBranch = "main",
    [string]$ParentDir = "..",
    [switch]$AllowLegacyWorktree
)

$ErrorActionPreference = "Stop"

if (-not $AllowLegacyWorktree) {
    Write-Warning "scripts/bootstrap-four-engines.ps1 is a legacy helper. The repo now defaults to branch-first delivery in one local working directory."
    Write-Host "Current branch-first roster:"
    Write-Host "  codex/branch-model-feature-first"
    Write-Host "  codex/feature-merchant-commission-meow"
    Write-Host "  codex/feature-guild-order-submit"
    Write-Host "  codex/shared-entry-navigation"
    Write-Host "  codex/shared-material-catalog"
    Write-Host ""
    Write-Host "Use git branch switching instead of local worktree bootstrapping."
    Write-Host "If you truly need the retired worktree bootstrap, rerun this script with -AllowLegacyWorktree."
    exit 1
}

$engines = @(
    @{
        Name = "Engine A"
        Branch = "codex/core-runtime-orchestration"
        Folder = "RoxAutoScript-wt-engine-a-runtime"
        Status = "legacy"
        Model = "gpt-5.4"
    },
    @{
        Name = "Engine B"
        Branch = "codex/gui-console-operator"
        Folder = "RoxAutoScript-wt-engine-b-gui"
        Status = "legacy"
        Model = "gpt-5.4"
    },
    @{
        Name = "Engine C"
        Branch = "codex/vision-lab-calibration-tools"
        Folder = "RoxAutoScript-wt-engine-c-vision"
        Status = "legacy"
        Model = "gpt-5.4"
    },
    @{
        Name = "Engine D"
        Branch = "codex/task-daily-ui"
        Folder = "RoxAutoScript-wt-engine-d-tasks"
        Status = "legacy"
        Model = "gpt-5.4"
    }
)

function Get-ExistingWorktreeMap {
    $map = @{}
    $currentWorktree = $null

    foreach ($line in (git worktree list --porcelain)) {
        if ($line -like "worktree *") {
            $currentWorktree = $line.Substring(9)
            continue
        }

        if ($line -like "branch refs/heads/*") {
            $branchName = $line.Substring(18)
            $map[$branchName] = $currentWorktree
        }
    }

    return $map
}

Write-Warning "Running legacy four-engine worktree bootstrap."
$existingWorktrees = Get-ExistingWorktreeMap

foreach ($engine in $engines) {
    $targetPath = Join-Path $ParentDir $engine.Folder
    Write-Host ""
    Write-Host "$($engine.Name) | branch=$($engine.Branch) | model=$($engine.Model) | status=$($engine.Status)"

    if ($existingWorktrees.ContainsKey($engine.Branch)) {
        Write-Host "Already attached at $($existingWorktrees[$engine.Branch])"
        continue
    }

    if (Test-Path $targetPath) {
        throw "Target path already exists and is not registered to the branch: $targetPath"
    }

    git show-ref --verify --quiet ("refs/heads/" + $engine.Branch)
    $branchExists = $LASTEXITCODE -eq 0

    if ($branchExists) {
        git worktree add $targetPath $engine.Branch
    }
    else {
        git worktree add $targetPath -b $engine.Branch $BaseBranch
    }

    Write-Host "Created $targetPath"
}

Write-Host ""
Write-Host "Legacy 4-engine worktree bootstrap complete."
