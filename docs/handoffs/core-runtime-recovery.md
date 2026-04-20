# Core Runtime Recovery Handoff

Track: core-runtime-recovery

Scope: execution and recovery side of Gate 2/3 within `core`, `emulator`, `logs`, and `profiles`; no `app` or `vision` changes.

Files changed:
- `src/roxauto/core/models.py`
- `src/roxauto/core/commands.py`
- `src/roxauto/core/runtime.py`
- `src/roxauto/core/events.py`
- `src/roxauto/core/__init__.py`
- `src/roxauto/emulator/execution.py`
- `src/roxauto/emulator/__init__.py`
- `src/roxauto/logs/audit.py`
- `src/roxauto/logs/__init__.py`
- `src/roxauto/profiles/store.py`
- `src/roxauto/profiles/__init__.py`
- `docs/architecture-contracts.md`
- `tests/core/test_commands.py`
- `tests/core/test_models.py`
- `tests/core/test_runtime.py`
- `tests/emulator/test_execution.py`
- `tests/profiles/test_store.py`

Public APIs added or changed:
- Shared contracts: `PreviewFrame`, `StopCondition`, `TaskManifest`, `FailureSnapshotMetadata`
- Routing contracts: `CommandRoute`, `CommandRouteKind`, `CommandRouter`, `CommandRoutingError`
- Execution services: `ScreenshotCapturePipeline`, `ActionExecutor`, `HealthCheckService`
- Profile contracts: `CalibrationProfile`, `InstanceProfileOverride`
- Audit helpers: `preview_audit_payload`, `failure_snapshot_audit_payload`, `write_preview_audit`, `write_failure_snapshot_audit`

Contract changes:
- `TaskSpec` now carries optional `manifest`, `stop_conditions`, and `metadata`.
- `TaskRun` now records optional `stop_condition`, `failure_snapshot`, and `preview_frame`.
- Architecture docs now treat preview capture, failure snapshot metadata, calibration, and per-instance overrides as shared contracts.

Assumptions:
- Stop conditions are evaluated from `TaskSpec.stop_conditions` and optional `TaskManifest.stop_conditions`.
- Failure snapshots are metadata records; no image processing or vision logic was added here.
- Structured audit payloads can carry nested dataclasses and are serialized by the existing JSON-line sink.

Verification performed:
- `python -m unittest discover -s tests -t .` passed with 20 tests.
- `PYTHONPATH=src python -m roxauto doctor` passed and reported one discovered MuMu instance.

Known limitations:
- `refresh`, `start_queue`, `pause`, `stop`, and `emergency_stop` are routed and recorded, but runtime ownership for queue state changes stays outside `emulator`.
- Preview capture currently wraps the adapter screenshot path; thumbnail generation is not implemented.

Blockers:
- None.

Recommended next step:
- Run the unit suite, then merge this branch into the main runtime track so the GUI and task tracks can build on the new contracts.
