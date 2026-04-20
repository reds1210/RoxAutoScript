# Core Runtime Orchestration Handoff

## Summary

- Added a runtime coordinator that owns per-instance runtime context, queue draining, command dispatch, health checks, preview capture, and profile binding.
- Extended shared runtime contracts with `ProfileBinding`, `InstanceRuntimeContext`, and `CommandDispatchResult`.
- Tightened instance lifecycle handling with validated status transitions in `InstanceRegistry`.

## Changed Files

- `src/roxauto/core/models.py`
- `src/roxauto/core/instance_registry.py`
- `src/roxauto/core/queue.py`
- `src/roxauto/core/commands.py`
- `src/roxauto/core/runtime.py`
- `src/roxauto/profiles/store.py`
- `src/roxauto/core/__init__.py`
- `docs/architecture-contracts.md`
- `tests/core/test_instance_registry.py`
- `tests/core/test_models.py`
- `tests/core/test_runtime.py`
- `tests/profiles/test_store.py`

## Verification

- `python -m unittest discover -s tests -t .`
- Result: `33` tests passed

## Blockers

- `app` still needs to consume `InstanceRuntimeContext` and `CommandDispatchResult`.
- `vision` is still using static preview data; real GUI preview plumbing should connect to `RuntimeCoordinator`.

## Next Step

- Wire `app` controls to `RuntimeCoordinator.dispatch_command()` and `RuntimeCoordinator.get_runtime_context()`.
