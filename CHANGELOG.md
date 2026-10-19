# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-10-19

### Added
- Loyalty & Cohorts page: repeat rate after an on-time, late or low-review first order; cohorts by first-purchase month.
- Delivery page (1600 x 1600): seller-handling vs carrier-transit days, weekday heat map, holiday weeks, cart size,
  sample comments by theme.
- Pareto of late orders by state and same-state vs interstate matrix; volume-vs-late scatter by month.
- Definitions page (metric dictionary driven by a DAX table) reachable from an info button on every page.
- Display names for every column shown to users; Holidays table; measure-only `Measures` table.

## [0.2.0] - 2026-10-18

### Added
- Branded 1600 × 900 canvas with page background and fictitious brand (`powerbi/branding/`).
- Power Query parameters `SnowflakeServer`, `SnowflakeWarehouse`, `SnowflakeRole`.
- CI: SQLFluff lint, PBIR schema validation and generator drift check, semantic-model diff comment,
  AI review of SQL changes, on-demand warehouse checks; Dependabot, CODEOWNERS, templates, pre-commit.
- Deterministic `lineageTag`s and visual names in the generator.

### Fixed
- `On-time Delivery %` returned 100 % for periods with no deliveries (now BLANK).
- "On time" measures filtered with `is_late = FALSE()` also matched NULL (canceled / in-progress orders).
- Themes chart used an invalid visual type; what-if parameter table column definition.

## [0.1.0] - 2026-10-17

### Added
- Snowflake layers RAW → STG → MARTS, semantic view `SV_ORDERS`, reconciliation checks.
- Generated PBIP: 10 tables, 49 measures, 5 pages (overview, delivery vs experience, where, recommendations, appendix).
- Rule-based classification of 1–2 star review comments into themes.
