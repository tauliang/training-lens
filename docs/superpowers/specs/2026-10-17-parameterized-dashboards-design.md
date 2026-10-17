# Parameterized dashboards: proposed design

Status: approved by the user on 2026-10-17; implementation in progress.

The user wants existing panels consolidated into a minimal set of reusable, parameterized panels. Choices must be populated from lookups derived from actual data; legends and units must follow the selected metric. Keep the ten existing dashboard routes and their useful workflows. Target 28 visible panels instead of the current 77, including essential tables and operator information.

## Proposed panel inventory

| Dashboard | Target panels | Contents and selectors |
|---|---:|---|
| Overview | 3 | Selected-volume summary; volume trend (activities/distance/moving hours/elevation, time grain, sport); recent activities |
| Training | 3 | Effort/time/HR-zone trend; selected configured goal; activity/training log |
| Run Performance | 3 | Distance/pace/speed/cadence trend; selected best-effort distance; comparable runs |
| Activity Detail | 3 | Activity summary; one telemetry chart (HR/pace/speed/elevation/cadence/measured power); details table (laps/splits/zones/exercises) |
| Vitals | 3 | Exercise-HR/recorded-weight trend; HR-zone history; coverage and unavailable measurements |
| Social | 4 | Network history; engagement history; follower ranking/roster table; current counts and data availability |
| Gear and Sports | 3 | Usage/performance trend by sport or gear; equipment thresholds; sport/strength details |
| Geography | 2 | Privacy-masked visits map; cell/sport coverage details |
| Data Health | 3 | Import readiness; selected coverage metric; quality/import/worker details |
| Setup | 1 | Installation/configuration guidance with navigation to Data Health for import status |
| **Total** | **28** | Consolidate repeated charts, retain distinct investigation and operational workflows |

Each analytical chart has a context-specific metric dropdown. A single time-grain control replaces separate weekly/monthly/yearly copies where the semantics match. Comparison presets add simultaneous series only within compatible units, for example average + peak exercise HR (bpm), HR zones (hours), or comments + kudos (counts). Volume can switch between count, distance and time; those values do not share an overlay scale. Maps and essential diagnostic tables retain dedicated representations.

## Metadata and data-backed availability

1. An administrator-owned metric catalog defines supported metric IDs, group, label, source, allowed aggregation, dimension, canonical/display units, conversion factors, precision, time basis and prerequisites. The catalog is data, not executable SPL.
2. A scheduled native search builds an availability lookup from reconciled indexed records, keyed by snapshot, metric, sport and gear. It records valid observation counts, source availability, coverage and refresh time. Only ready snapshots can supply options. Existing indexed records support this refactor without another ingestion schema change.
3. A dimension lookup supplies actual sports, gear, configured goals and available best-effort targets. Replace hard-coded sport lists and free-form gear selection where appropriate.
4. The dropdown joins the catalog to availability for the selected snapshot/sport/gear. Availability describes the snapshot; charts still honor the selected period. A metric present in history but absent in the chosen period produces an explicit empty state.
5. Missing cache, no import, no valid metric, stale bookmarked IDs and a newly ready snapshot awaiting refresh have deterministic defaults/status. Never display an unsupported metric as zero. Keep a small availability table for absent VO2 max and unavailable received social interactions.

## Calculations, labels and units

Preserve current validation and definitions. Activity counts are distinct current-snapshot events. Speed is summed valid distance / summed valid moving time; pace is summed time / summed distance. Exercise HR and cadence use eligible-duration weighting. Peaks use max, best efforts use min, and coverage uses numerator/denominator rather than averaging percentages. Zero-denominator ratios remain missing.

Metric/Imperial selection applies only to dimensions with a verified conversion. HR remains bpm, confirmed running cadence remains steps/min, and percentages/counts retain their own units. Recorded weight stays in original export units until its source unit is known. Cadence conversion remains explicit. Ski speed remains whole-activity moving speed, including recorded lifts/traverses. Follower observations retain import-date semantics and incoming engagement requires supplied actor-level records.

Bind chart title, axis label, legend, tooltip unit and table precision to the same selected catalog definition. Emit safe result-series labels such as `Run · Average exercise HR (bpm)` and `Alpine Ski · Moving speed (MPH)`. Selection IDs are quoted values, not injected field names or SPL fragments. Registry field/aggregation identifiers are validated against a fixed supported allowlist.

## Splunk implementation constraints

- Main ingestion index: `strava`. Separate privacy/operational indexes: `strava_private`, `strava_shared`, `strava_ops`.
- Feature branch: `feat/implement-training-lens`.
- Splunk Enterprise 10.x; test specifically 10.0.11 and 10.4.4.
- Python 3.9-compatible app code and Python 3.13 verification.
- Native Dashboard Studio, CSV lookups, SPL and app configuration; no new JavaScript runtime, external service, database or credentials.
- Reuse aggregated base/chain searches; never feed an unbounded raw stream to a post-process search or truncate silently.
- Choose only supported metrics for the active group; preserve snapshot reconciliation, access roles, reporting timezone, quality modes, full-year/comparable-YTD behavior and drilldowns.
- Runtime lookup contents remain private; administrator writes, athlete-role reads. Package only static catalog data and header-only runtime-cache seeds.
- Preserve existing dashboard URLs and the activity_id/snapshot drilldown tokens.
- Data refresh publishes a complete cache for ready snapshots; an error retains the last usable version and reports staleness. Fresh snapshot cache misses show pending, not a previous snapshot's metric availability.

## Acceptance

Every existing metric/workflow maps to a selector option, contextual table, or explicit data-gap status. The ten routes have the 28-panel target inventory. Titles, numeric values and units agree after selection changes. Validity/weighting, time bounds and missing-data behavior remain correct. All metric/group/unit combinations execute on both tested Enterprise versions; browser checks exercise cascading dropdowns, default/reset behavior, legends, snapshots and drilldowns. Compare search count, concurrency/queuing and latency to the 77-panel baseline. Finish with reproducible packaging, AppInspect and updated synthetic screenshots.

## Official implementation references

- [Data-backed dropdown inputs](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/make-dashboards-dynamic-and-interactive/inputs/dropdown-and-multiselect)
- [Native base and chain searches](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/use-data-sources/chain-searches-together-with-a-base-search-and-chain-searches)
- [Lookup semantics in Enterprise 10.0](https://help.splunk.com/en/splunk-enterprise/search/spl-search-reference/10.0/search-commands/lookup)

The first implementation task verifies the exact title/axis/input bindings on both target versions; examples from later versions are not assumed compatible with 10.0.
