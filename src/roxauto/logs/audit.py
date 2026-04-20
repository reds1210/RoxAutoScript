from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from roxauto.core.events import EVENT_FAILURE_SNAPSHOT_RECORDED, EVENT_PREVIEW_CAPTURED
from roxauto.core.models import FailureSnapshotMetadata, PreviewFrame
from roxauto.core.serde import to_primitive
from roxauto.core.time import utc_now


@dataclass(slots=True)
class AuditRecord:
    name: str
    payload: dict[str, Any]
    emitted_at: object = field(default_factory=utc_now)


def preview_audit_payload(
    preview_frame: PreviewFrame,
    *,
    run_id: str | None = None,
    task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": run_id,
        "task_id": task_id,
        "preview_frame": preview_frame,
    }
    if metadata:
        payload["metadata"] = metadata
    return payload


def failure_snapshot_audit_payload(
    failure_snapshot: FailureSnapshotMetadata,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": failure_snapshot.run_id,
        "task_id": failure_snapshot.task_id,
        "instance_id": failure_snapshot.instance_id,
        "failure_snapshot": failure_snapshot,
    }
    if metadata:
        payload["metadata"] = metadata
    return payload


def write_preview_audit(
    sink: Any,
    preview_frame: PreviewFrame,
    *,
    run_id: str | None = None,
    task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    sink.write(
        EVENT_PREVIEW_CAPTURED,
        preview_audit_payload(preview_frame, run_id=run_id, task_id=task_id, metadata=metadata),
    )


def write_failure_snapshot_audit(
    sink: Any,
    failure_snapshot: FailureSnapshotMetadata,
    *,
    metadata: dict[str, Any] | None = None,
) -> None:
    sink.write(
        EVENT_FAILURE_SNAPSHOT_RECORDED,
        failure_snapshot_audit_payload(failure_snapshot, metadata=metadata),
    )


class JsonLineAuditSink:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, name: str, payload: dict[str, Any]) -> None:
        record = AuditRecord(name=name, payload=payload)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(to_primitive(record), ensure_ascii=False) + "\n")
