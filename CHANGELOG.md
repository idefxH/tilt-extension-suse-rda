# Changelog

## [0.4.0] - 2026-05-05

_Multi-instance same-chart-type support._

### Added

- **Multi-instance:** `filter_enabled_deps` expands Chart.yaml with aliased entries for multi-instance types
- Add alias-aware `workload_name_for()` — per-binding k8s_resource registration
- Add port collision avoidance for multi-instance same-type services
- Add `enabled_charts()` returns aliased names for multi-instance types

### Fixed

- Fix `_chart_enabled` to check aliased blocks (`grafana-dashboards.enabled`)
- Remove debug print from workload registration loop

### Changed

- Replace CLI references: `rda add-service` → `rda service add`, `rda add-datasource` → `rda service wire`

## [0.3.4] - 2026-05-04

### Added

- Read service ports from dsl-mappings.yaml (zero-config, data-driven)
- Remap privileged ports (<1024) to `port+10000` for local port-forwards

## [0.3.3] - 2026-05-04

### Fixed

- Add `heroku/procfile` to Java buildpack defaults (fixes "no default process" crash)

[0.4.0]: https://github.com/idefxH/tilt-extension-suse-rda/releases/tag/v0.4.0
[0.3.4]: https://github.com/idefxH/tilt-extension-suse-rda/releases/tag/v0.3.4
[0.3.3]: https://github.com/idefxH/tilt-extension-suse-rda/releases/tag/v0.3.3
