from __future__ import annotations

from roxauto.tasks.catalog import TaskFoundationRepository
from roxauto.tasks.models import TaskBlueprint, TaskPackCatalog


def load_daily_ui_catalog(repository: TaskFoundationRepository | None = None) -> TaskPackCatalog:
    repo = repository or TaskFoundationRepository.load_default()
    return repo.load_pack_catalog_for_pack("daily_ui")


def load_daily_ui_blueprints(repository: TaskFoundationRepository | None = None) -> list[TaskBlueprint]:
    repo = repository or TaskFoundationRepository.load_default()
    return repo.discover_blueprints(pack_id="daily_ui")
