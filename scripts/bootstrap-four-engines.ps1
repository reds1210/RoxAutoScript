param(
    [string]$BaseBranch = "main",
    [string]$ParentDir = ".."
)

$ErrorActionPreference = "Stop"

$engines = @(
    @{
        Name = "Engine A"
        Branch = "codex/core-runtime-orchestration"
        Folder = "RoxAutoScript-wt-engine-a-runtime"
        Status = "active"
        Model = "gpt-5.4"
    },
    @{
        Name = "Engine B"
        Branch = "codex/gui-console-operator"
        Folder = "RoxAutoScript-wt-engine-b-gui"
        Status = "active"
        Model = "gpt-5.4"
    },
    @{
        Name = "Engine C"
        Branch = "codex/vision-lab-calibration-tools"
        Folder = "RoxAutoScript-wt-engine-c-vision"
        Status = "active"
        Model = "gpt-5.4"
    },
    @{
        Name = "Engine D"
        Branch = "codex/task-daily-ui"
        Folder = "RoxAutoScript-wt-engine-d-tasks"
        Status = "standby"
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
Write-Host "4-engine bootstrap complete."
