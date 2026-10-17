# Parameterized Dashboards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task after user review. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate 77 panels into approximately 28 useful panels across the ten existing dashboards, with data-backed metric selectors and consistent dynamic labels/units.

**Architecture:** Join a curated, non-executable metric catalog to availability/dimension lookups generated from ready indexed snapshots. Shared chart/query builders generate native Studio panels with server-side aggregation and compatible comparison presets. Existing import and privacy contracts remain intact.

**Tech Stack:** Splunk Enterprise 10.x, Dashboard Studio, SPL, CSV lookups, Python 3.9/3.13, unittest, AppInspect.

**Spec:** [Proposed design](../specs/2026-10-17-parameterized-dashboards-design.md). Status: approved by the user on 2026-10-17; implementation in progress.

## Global Constraints

- Main ingestion index: `strava`. Separate privacy/operational indexes: `strava_private`, `strava_shared`, `strava_ops`.
- Feature branch: `feat/implement-training-lens`.
- Splunk Enterprise 10.x; test specifically 10.0.11 and 10.4.4.
- Python 3.9-compatible app code and Python 3.13 verification.
- Native Dashboard Studio, CSV lookups, SPL and app configuration; no new JavaScript runtime, external service, database or credentials.
- Preserve existing dashboard URLs and the activity_id/snapshot drilldown tokens.
- Runtime lookup contents remain private; administrator writes, athlete-role reads. Package only static catalog data and header-only runtime-cache seeds.

## Review Focus

- Switching sport/snapshot removes the selected metric: choose a valid default or explicit unavailable state; never relabel stale values.
- Unknown or mismatched units: retain original units or change the selected metric; never apply a guessed conversion or combine incompatible scales.
- No ready snapshot, partial indexing or failed lookup refresh: show pending/stale status and never publish incomplete availability.
- Unequal durations, missing sensors and zero baselines: preserve weighted denominators, nulls, comparison semantics and historical time bounds.
- High-cardinality categories and restricted roles: avoid hidden truncation, uncontrolled query fan-out and disclosure of private lookup contents.

## File responsibilities

| File | Responsibility |
|---|---|
| `build/training_lens/lookups/training_lens_metric_catalog.csv` | Static supported metric definitions; no athlete data or executable queries |
| `build/training_lens/lookups/training_lens_metric_availability.csv` | Header-only package seed; runtime cache maintained by scheduled search |
| `build/training_lens/lookups/training_lens_dimension_options.csv` | Header-only seed for observed sports, gear, goals and effort targets |
| `build/training_lens/default/transforms.conf` | Named CSV lookup definitions |
| `build/training_lens/default/savedsearches.conf` | Ready-snapshot cache refresh and health status |
| `build/training_lens/metadata/default.meta` | App-scoped lookup and scheduled-search permissions |
| `tools/metric_catalog.py` | Catalog validation, supported aggregation/unit mappings and safe query generation |
| `tools/dashboard_components.py` | Shared dropdown, trend, summary, comparison and detail-table builders |
| `tools/generate_dashboards.py` | Ten page layouts and their minimal panel composition |
| `tools/package.py` | Allowlist static lookups; reject populated runtime cache seeds |
| `tests/test_metric_catalog.py`, `tests/test_metric_components.py` | Metadata, calculations, generated definitions and privacy contracts |
| `tools/verify_metric_selectors.py` | Installed lookup/selection/calculation/browser acceptance matrix |

## Task 1: Validate native bindings and lock the inventory

**Files:** Create `tools/verify_metric_selectors.py`; update the proposed design with measured compatibility notes.

**Interfaces:** Produce a compatibility record for lookup-backed dropdowns, first-result/reset behavior, dynamic title/axis/tooltip labels, and aggregated `ds.chain` searches on 10.0.11/10.4.4. No new production dependency.

- [ ] Create a synthetic compatibility dashboard using an in-memory activity fixture and a small private test lookup. Assert selection changes value, title, legend and display unit together; test a stale bookmarked ID and an empty option list.
- [ ] Execute it on both versions. Record supported native properties and use baseline-compatible bindings for the implementation.
- [ ] Map all 77 current panels to the design's 28 target panels and exact selector modes; verify no metric or operator workflow is lost.
- [ ] Commit the compatibility harness and final inventory.

## Task 2: Ship the catalog and data-derived lookups

**Files:** Create the three CSVs and `default/transforms.conf`; modify saved searches, metadata and package builder; create `tools/metric_catalog.py` and `tests/test_metric_catalog.py`.

**Interfaces:** `load_catalog(path: Path) -> list[dict]`; `validate_catalog(rows: list[dict]) -> None`. Catalog fields: `metric_id,group_id,label,source_kind,source_field,aggregation_key,dimension,canonical_unit,metric_unit,imperial_unit,metric_factor,imperial_factor,precision,time_basis,prerequisite,sort_order`.

Availability rows: `snapshot_id,metric_id,sport,gear,source_available,valid_count,total_count,status,refreshed_at`. Dimension rows: `snapshot_id,dimension,value,label,sort_order`. Use dimension-neutral rows for summaries that are not sport/gear-specific.

- [ ] Write failing tests for duplicate IDs, unsupported source/aggregation keys, invalid conversion factors, unknown weight units and cadence prerequisites. Assert unsupported definitions cannot become executable SPL.
- [ ] Implement the catalog loader/validator with explicit source and aggregation allowlists; no `map`, runtime `eval` of CSV strings, or raw token field-name expansion.
- [ ] Add scheduled native lookup refresh from ready snapshots only. Publish complete tables; validate refresh failure retains usable prior data and exposes staleness. A cache miss for a new snapshot is pending, not inherited availability.
- [ ] Test no-ready/partial snapshots, accepted snapshot replacements, missing incoming social sources, absent VO2 max, unconfirmed cadence and real sport/gear option discovery.
- [ ] Apply private app-scoped permissions. Test athlete access, viewer denial and administrator-only writes. Package tests reject populated runtime seeds and exclude private fixtures.
- [ ] Run `python -m unittest discover -v`, package reproducibility checks and live lookup acceptance on both versions; commit.

## Task 3: Build the reusable metric and chart pipeline

**Files:** Create `tools/dashboard_components.py`, `tests/test_metric_components.py`; extend `tools/metric_catalog.py` and the live verifier.

**Interfaces:** `metric_options(group_id, snapshot_tokens) -> dict` builds the native lookup-backed input. `metric_query(group_id, metric_token, grain_token) -> str` builds escaped, allowlisted SPL. `trend_panel(group_id, default_metric, dimensions) -> dict` produces chart/input/data-source definitions. Each query emits bounded `bucket,series_label,value,unit,coverage` rows before pivoting.

- [ ] Write failing calculation tests using unequal-duration fixtures: exercise HR 100 bpm × 100 s and 160 bpm × 300 s must produce 145 bpm; 10 miles/1 hour plus 90 miles/3 hours must produce 25 MPH; zero denominators stay null.
- [ ] Implement the known aggregation mappings, Metric/Imperial factors, precision and explicit cadence conversion. Original-unit weight, bpm, steps/min and counts do not inherit irrelevant unit conversions.
- [ ] Generate title, axis, legend and tooltip formatting from the same selected definition. Test `Run · Average exercise HR (bpm)` and `Alpine Ski · Moving speed (MPH)` with matching values.
- [ ] Add compatible comparison presets, such as average + peak HR and comments + kudos. Test rejection of mixed bpm/weight or pace/distance overlays.
- [ ] Implement selection reset/default behavior and empty/pending/stale states validated in Task 1. Test the label/value transition after changing sport and pinned snapshot.
- [ ] Reuse aggregated base/chain searches, with server-side binning for telemetry. Test cardinality limits and explicit category handling; never silently truncate raw streams or categories.
- [ ] Run unit tests and live query matrix on both versions; commit.

## Task 4: Migrate the ten dashboards to the minimal inventory

**Files:** Modify `tools/generate_dashboards.py`, generated views and dashboard tests. Preserve navigation view IDs and existing drilldown token names.

**Interfaces:** Consume Task 3 components and Task 2 catalog IDs. Emit the 28-panel inventory in the linked design, with one shared metric selection driving summary/chart pairs where applicable.

- [ ] First migrate Vitals and Social: consolidate repeated time-grain charts; retain measurement/interaction availability and observation-date semantics. Verify unknown units and missing incoming records cannot be selected as measured values.
- [ ] Migrate Overview, Run Performance and Gear/Sports: reuse one volume/performance trend per context, with period/grain, metric, split and annual comparison controls. Preserve skiing definitions and selected-distance best efforts.
- [ ] Migrate Training and Activity Detail: combine load/zone modes where the chart family permits; one telemetry chart and one detail-mode table. Measured power is offered only when a power stream exists.
- [ ] Consolidate Data Health coverage/status/details, retain the useful map and its coverage/details, and reduce Setup to configuration guidance linked to Data Health.
- [ ] Check every original metric against the mapping from Task 1, native generation drift, saved links, details drilldown, configured goals, quality modes and active-snapshot filtering.
- [ ] Run the full suite and migrate/verifier checks on both versions; commit each coherent migration batch.

## Task 5: Verify performance, package and deliver

**Files:** Update Enterprise verifiers, validation/installation docs, screenshots and release artifacts.

**Interfaces:** `verify_metric_selectors.py` enumerates registered group/metric/unit/grain/compatible-preset combinations and validates the installed app. It records option sources, results, labels and limits, without publishing private data.

- [ ] Execute every supported combination with missing/invalid fields, empty periods, absent lookups, stale snapshots and hostile token values; compare against independent fixture totals.
- [ ] Browser-test cascading selectors, change/reset behavior, metric-dependent legend/units, bookmarks, navigation and narrow layouts on both tested versions.
- [ ] Measure initial search jobs, index scans, queued searches and representative latency versus the 77-panel baseline. Confirm one shared lookup-option source per page and selected metric queries only; do not increase global concurrency limits.
- [ ] Rebuild the deterministic `.spl`; confirm only static/header-only lookups ship. Run AppInspect, role/access checks and current unit/Enterprise/browser suites.
- [ ] Update docs with chart defaults and source/measurement caveats, capture synthetic screenshots, request final code review, and push the approved implementation to the existing PR.

## Review and execution

Review the proposed 28-panel inventory and selector behavior before implementation. Recommended execution is native, in this session, with an independent final code review: the tasks share catalog and query interfaces, so a single implementation path keeps those contracts consistent. No code for this refactor should be implemented until the user approves this plan.
