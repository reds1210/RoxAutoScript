# Task Foundations Asset Conventions

- Golden screenshots use `tests/tasks/fixtures/goldens/<pack>/<task_slug>/<screen_slug>/`.
- Dotted `task_id` values are normalized to snake_case when building screenshot paths.
- Template anchors under `assets/templates/*/manifest.json` are treated as placeholders until real captures exist.
- Missing anchors stay explicit in `asset_inventory.json`; they should not be silently synthesized by task code.
