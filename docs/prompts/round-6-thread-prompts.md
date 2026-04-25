# Round 6 Thread Prompts

Legacy note:

- this prompt pack describes the retired engine/worktree model
- use `docs/engine-roster.md`, `docs/worktree-playbook.md`, and `docs/prompts/feature-branch-thread-prompts.md` for new branch-first work

Use these prompts for new top-level Codex threads in the round-6 `claim_rewards` production-hardening wave.

Model:

- `gpt-5.4`

Important:

- each prompt is for one top-level thread, not a subagent
- each thread should stay on its dedicated worktree
- each thread should read `main`, handoffs, and the round-6 brief instead of assuming other thread chat history

## Worktree Map

- `Engine C` -> `C:\code\RoxAutoScript-wt-vision-claim-rewards-live` -> `codex/vision-claim-rewards-live-captures`
- `Engine D` -> `C:\code\RoxAutoScript-wt-task-claim-rewards-runtime` -> `codex/task-claim-rewards-runtime-seam`
- `Engine A` -> `C:\code\RoxAutoScript-wt-core-runtime-step-telemetry` -> `codex/core-runtime-step-telemetry`
- `Engine B` -> `C:\code\RoxAutoScript-wt-gui-claim-rewards-production` -> `codex/gui-claim-rewards-production-telemetry`
- `Engine E` optional -> `C:\code\RoxAutoScript-wt-claim-rewards-goldens` -> `codex/claim-rewards-goldens`

## Recommended Start Order

1. `Engine E` only if live captures are the current blocker
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

## Shared Opening

Paste this first in each new thread:

```text
你是在一條新的 top-level thread 內工作，不是 subagent。不要再開代理取代這條 thread 的主要工作。

先閱讀：
- README.md
- docs/worktree-playbook.md
- docs/engine-roster.md
- docs/architecture-contracts.md
- docs/round-6-claim-rewards-production-hardening.md
- 你這條線相關的 handoff
- main 最新程式碼

工作方式：
- 先用 5 到 10 句整理目前狀態、ownership、依賴、風險
- 再列出本輪要做的具體項目
- 直接在本 thread 對應的 worktree 內實作
- 完成後跑相關測試
- 更新 handoff 到 docs/handoffs/
- 最後回報：
  - Changed files
  - Tests run
  - What shipped
  - Blockers
  - Recommended next step

限制：
- 不要改不屬於你 ownership 的目錄
- 這一輪只允許推進 daily_ui.claim_rewards
- 不要擴到 guild_check_in / odin / 第二個任務
- 若依賴別條線，優先讀 main 和 docs/handoffs/，不要假設你知道別條 thread 的聊天內容
```

## Engine C Prompt

```text
你是 Engine C，負責 vision / templates / failure inspection。你在 branch codex/vision-claim-rewards-live-captures，worktree 是 C:\code\RoxAutoScript-wt-vision-claim-rewards-live。

ownership：
- src/roxauto/vision/
- assets/templates/
- docs/vision/
- tests/vision/
- docs/handoffs/

本輪目標：
- 針對 daily_ui.claim_rewards 用 live zh-TW ROX captures 取代或補強現有 screenshot-style curated baselines
- 保持既有三個 anchor 的契約穩定：
  - daily_ui.reward_panel
  - daily_ui.claim_reward
  - daily_ui.reward_confirm_state
- 讓 failure / inspection payload 能更可信地指出：哪個 anchor 沒過、目前 threshold、多半是哪張 runtime 圖、對應哪張 template 或 reference image
- 讓 readiness 能分辨 live、curated stand-in、placeholder、inventory mismatch

不要碰：
- src/roxauto/core/
- src/roxauto/emulator/
- src/roxauto/tasks/
- src/roxauto/app/

驗收：
- claim_rewards 的基線素材更接近真實 ROX 場景
- failure inspection 仍保持 GUI 可直接吃的 flatten surface
- tests/vision 綠
- handoff 清楚寫出哪些素材已是 live capture、哪些仍是 stand-in
```

## Engine D Prompt

```text
你是 Engine D，負責 tasks。你在 branch codex/task-claim-rewards-runtime-seam，worktree 是 C:\code\RoxAutoScript-wt-task-claim-rewards-runtime。

ownership：
- src/roxauto/tasks/
- tests/tasks/
- docs/handoffs/

本輪目標：
- 只推進 daily_ui.claim_rewards
- 正式整理 runtime seam，讓 task builders / runtime inputs / TaskSpec builders 可由 runtime 註冊與 enqueue 路徑直接吃
- 保持 failure_reason、outcome_code、inspection_attempts、signals、telemetry 等結果結構穩定、機器可讀
- 對齊 foundations inventory / readiness 與現在已 curated 的 claim_rewards 資產狀態

不要碰：
- src/roxauto/core/
- src/roxauto/emulator/
- src/roxauto/app/
- src/roxauto/vision/
- 不要開第二個任務

驗收：
- claim_rewards 的 runtime seam 更清楚
- task-side failure/result 不需要下游再 parse message
- tests/tasks 綠
- handoff 清楚寫出 A 與 B 下一步應讀哪些 task-owned signal
```

## Engine A Prompt

```text
你是 Engine A，負責 runtime / emulator / profiles / logs。你在 branch codex/core-runtime-step-telemetry，worktree 是 C:\code\RoxAutoScript-wt-core-runtime-step-telemetry。

ownership：
- src/roxauto/core/
- src/roxauto/emulator/
- src/roxauto/logs/
- src/roxauto/profiles/
- tests/core/
- tests/emulator/
- tests/profiles/
- 必要時 docs/architecture-contracts.md
- docs/handoffs/

本輪目標：
- 把 task-side structured failure / outcome / inspection signals 接進 runtime-owned telemetry
- 讓 active_task_run、last_task_run、last_failure_snapshot 在 retry 與 restart 後仍有穩定權威性
- 補 runtime registration / enqueue seam，讓 GUI 不是 claim_rewards 執行狀態的 source of truth
- 保持 production-oriented execution path，不做無關的大規模重構

不要碰：
- src/roxauto/app/
- src/roxauto/vision/
- src/roxauto/tasks/ 的 task 定義本身

驗收：
- runtime telemetry 已足夠讓 GUI 不再自己補 task state
- sticky failure inspection 在 retry 後不會丟掉前一次失敗上下文
- tests/core + tests/emulator 綠
- handoff 清楚寫出 B 應怎麼接新的 runtime signal
```

## Engine B Prompt

```text
你是 Engine B，負責 app GUI。你在 branch codex/gui-claim-rewards-production-telemetry，worktree 是 C:\code\RoxAutoScript-wt-gui-claim-rewards-production。

ownership：
- src/roxauto/app/
- assets/ui/
- tests/app/
- docs/handoffs/

本輪目標：
- 保持 daily_ui.claim_rewards 是主畫面唯一主流程
- 盡量只消費 runtime/task/vision 已提供的 signal，不再發明 app-owned workflow state
- 把 failure / diagnostics / next-step guidance 再收斂一步，讓操作者能直接知道應該調哪個 anchor、哪個區域、哪個 threshold
- calibration 與 capture editor 仍保持 viewer-first，除非下層已提供 production signal

不要碰：
- src/roxauto/core/
- src/roxauto/emulator/
- src/roxauto/vision/
- src/roxauto/tasks/

驗收：
- GUI guidance 更清楚，但 task state 仍來自 runtime/task/vision
- 沒有把 viewer-only surface 偽裝成 runtime-owned signal
- tests/app 綠
- handoff 清楚標出哪些仍是 operator aid、哪些已是 production telemetry
```

## Engine E Prompt

```text
你是 Engine E，負責 live screenshots / goldens。你在 branch codex/claim-rewards-goldens，worktree 是 C:\code\RoxAutoScript-wt-claim-rewards-goldens。

ownership：
- assets/templates/
- tests/tasks/fixtures/
- docs/vision/

本輪目標：
- 只為 daily_ui.claim_rewards 收集 live zh-TW ROX screenshots / goldens
- 至少整理三種畫面：
  - reward panel open
  - reward panel claimable
  - reward confirmation modal
- 文件化每張圖在證明什麼、對應哪個 anchor / step / failure case
- 不改 core / app / task logic

驗收：
- 有可被 C/D 使用的 live screenshots 或 goldens
- docs/vision 有清楚說明
- 不混入其他任務資產
```
