# gui-console-operator handoff

## Changed files
- `src/roxauto/app/viewmodels.py`
- `src/roxauto/app/shell.py`
- `src/roxauto/app/__init__.py`
- `assets/ui/operator_console.qss`
- `tests/app/test_viewmodels.py`

## Verification
- `python -m unittest discover -s tests/app -t .`
- `python -m unittest discover -s tests -t .`

## What shipped
- Added operator-console app state for instance detail, queue pane, log pane, manual controls, and global emergency-stop state.
- Reworked the PySide6 shell into a first-wave operator console with instance list, detail pane, queue pane, log pane, preview/calibration/recording/anchor/failure panes, and manual control dispatch built on shared command routing.
- Added a small UI stylesheet so the shell is easier to scan during multi-instance operation.

## Blockers
- Manual controls currently route through the shared `CommandRouter` and emit local operator events only; runtime execution wiring still depends on Engine A exposing a live command/preview pipeline.
- Preview, queue, and log content are populated from sample state plus doctor output until runtime services are connected.

## Next step
- Replace the sample queue/event feeds in `shell.py` with live runtime/event-bus adapters once the runtime orchestration branch lands.
