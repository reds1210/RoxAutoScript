from __future__ import annotations

from pathlib import Path

from roxauto.core.events import EventBus
from roxauto.core.models import InstanceState, InstanceStatus, TaskSpec
from roxauto.core.runtime import TaskExecutionContext, TaskRunner, TaskStep, step_success
from roxauto.logs.audit import JsonLineAuditSink


def run_runtime_demo(log_dir: Path) -> int:
    log_dir.mkdir(parents=True, exist_ok=True)
    audit_path = log_dir / "runtime-demo.jsonl"
    audit_sink = JsonLineAuditSink(audit_path)
    event_bus = EventBus()

    instance = InstanceState(
        instance_id="mumu-demo",
        label="MuMu Demo",
        adb_serial="127.0.0.1:16384",
        status=InstanceStatus.READY,
    )

    steps = [
        TaskStep(
            step_id="load_home",
            description="Simulate reaching the ROX home screen",
            handler=lambda ctx: step_success(
                step_id="load_home",
                message=f"{ctx.instance.label} reached the home screen",
            ),
        ),
        TaskStep(
            step_id="claim_reward",
            description="Simulate claiming a deterministic reward",
            handler=lambda ctx: step_success(
                step_id="claim_reward",
                message="Daily reward claimed in demo mode",
            ),
        ),
    ]

    spec = TaskSpec(
        task_id="demo.daily_reward",
        name="Demo Daily Reward",
        version="0.1.0",
        entry_state="ready",
        steps=steps,
    )

    context = TaskExecutionContext(instance=instance, metadata={"mode": "demo"})
    runner = TaskRunner(event_bus=event_bus, audit_sink=audit_sink)
    run = runner.run_task(spec=spec, context=context)

    print(f"Run ID: {run.run_id}")
    print(f"Task: {run.task_id}")
    print(f"Status: {run.status.value}")
    print(f"Steps completed: {len(run.step_results)}")
    print(f"Audit log: {audit_path.resolve()}")
    return 0

