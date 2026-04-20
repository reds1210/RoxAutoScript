"""Structured logging package."""

from roxauto.logs.audit import (
    AuditRecord,
    JsonLineAuditSink,
    failure_snapshot_audit_payload,
    preview_audit_payload,
    write_failure_snapshot_audit,
    write_preview_audit,
)

__all__ = [
    "AuditRecord",
    "JsonLineAuditSink",
    "failure_snapshot_audit_payload",
    "preview_audit_payload",
    "write_failure_snapshot_audit",
    "write_preview_audit",
]

