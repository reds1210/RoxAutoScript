"""Task foundation package for pre-Gate-3 task assets and schemas."""

from roxauto.tasks.catalog import TaskFoundationRepository
from roxauto.tasks.models import (
    GoldenScreenshotCase,
    GoldenScreenshotConvention,
    TaskAssetInventory,
    TaskAssetKind,
    TaskAssetRecord,
    TaskAssetStatus,
    TaskBlueprint,
    TaskFixtureProfile,
    TaskImplementationState,
    TaskInventory,
    TaskInventoryRecord,
    TaskPackCatalog,
    TaskPackCatalogEntry,
    TaskStepBlueprint,
)

__all__ = [
    "GoldenScreenshotCase",
    "GoldenScreenshotConvention",
    "TaskAssetInventory",
    "TaskAssetKind",
    "TaskAssetRecord",
    "TaskAssetStatus",
    "TaskBlueprint",
    "TaskFixtureProfile",
    "TaskFoundationRepository",
    "TaskImplementationState",
    "TaskInventory",
    "TaskInventoryRecord",
    "TaskPackCatalog",
    "TaskPackCatalogEntry",
    "TaskStepBlueprint",
]

