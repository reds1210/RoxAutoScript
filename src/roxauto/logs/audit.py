from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from roxauto.core.serde import to_primitive
from roxauto.core.time import utc_now


@dataclass(slots=True)
class AuditRecord:
    name: str
    payload: dict[str, Any]
    emitted_at: object = field(default_factory=utc_now)


class JsonLineAuditSink:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, name: str, payload: dict[str, Any]) -> None:
        record = AuditRecord(name=name, payload=payload)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(to_primitive(record), ensure_ascii=False) + "\n")

