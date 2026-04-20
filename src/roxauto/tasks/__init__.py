"""Task foundation package for pre-Gate-3 task assets and schemas."""

from roxauto.tasks.catalog import TaskFoundationRepository
from roxauto.tasks.models import (
    GoldenScreenshotCase,
    GoldenScreenshotConvention,
    TaskBlueprint,
    TaskFixtureProfile,
    TaskImplementationState,
    TaskInventory,
    TaskInventoryRecord,
)

__all__ = [
    "GoldenScreenshotCase",
    "GoldenScreenshotConvention",
    "TaskBlueprint",
    "TaskFixtureProfile",
    "TaskFoundationRepository",
    "TaskImplementationState",
    "TaskInventory",
    "TaskInventoryRecord",
]

