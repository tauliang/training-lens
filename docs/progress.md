# Implementation ledger

Plan: Training Lens implementation, authorized October 17, 2026.

Pre-flight: summary Activity → importer → snapshot manifest → native dashboard searches; signatures will be pinned in tests. Stream revision → derived intervals → membership filter is the second shared interface. Packaging consumes generated dashboards and vendor allowlist.

Ruling: app ID and field prefix are training_lens / tl, as named by the user after the design; rename cost is mechanical.
Ruling: use a separate clone and feature branch for the target repository; preserve the unrelated workspace and all personal data outside Git.
Ruling: publish a reconciled immutable ready event rather than mutable CSV registry files. A single marker contains the snapshot identity and import order; all current activity and stream membership searches resolve that marker. This avoids partially published filesystem lookups and requires no management credentials. Cross-panel dispatch can straddle an activation; explicit snapshot selection pins a review session.

## Tasks

- [x] 1 Canonical parser and quality rules
- [x] 2 Safe archive lifecycle and deterministic spool
- [x] 3 Splunk input and reconciliation
- [x] 4 Native dashboards
- [x] 5 FIT and GPX decoding
- [x] 6 Derived intervals, best efforts, geography
- [x] 7 Package, compatibility validation, review and push

Task 1: complete — 7 parser tests RED (empty stub) → GREEN; private full-export count, SI distance, duration conflicts and effort disagreements matched independently measured baseline. No personal data stored in repository.

Task 2: complete — archive/lifecycle RED→GREEN, 12 tests pass. Root cause of the recovery assertion was missing notification of repaired chunks, corrected by comparing the prior manifest before rebuilding. Stable scans, content hashes, bounded nested decompression, explicit errors and independent snapshots covered.

Task 3: native config and reconciliation contract implemented; runtime acceptance pending. Logical groups reconcile distinct event IDs; duplicate physical events do not inflate counts.
Task 5: decoder RED→GREEN with synthetic FIT CRC and timestamp fixture, GPX extensions, coordinates, truncation and rejected XML declarations. Full private archive validation running.
Task 6: derived analysis RED→GREEN (HR intervals/pauses/gaps, interpolated best efforts, distance resets and privacy). Export privacy-zone masking has an independent integration fixture that failed with three leaked cells before the automatic exported-zone mask was added; now zero shared cells. Raw sample events never carry location.
Ruling: use only confirmed custom HR zones. Until configured, HR traces remain usable and zone panels explain missing configuration; do not silently treat the old exported maximum HR as current.

Task 4: eight native Dashboard Studio pages generated; filter tokens use SPL string escaping, empty snapshot selection fails closed, activity IDs are validated, and detail queries are bounded by current stream membership. Generator/package tests RED→GREEN. Browser and runtime SPL checks pending.

Private export acceptance: strict decoder processed every referenced activity file with zero quarantines; independently measured raw samples/laps and summary totals matched. Personal acceptance output stays in .private/.
Runtime environment: QEMU indexer crash isolated to disposable container, recreating with Rosetta. Bundled Python 3.9 tests passed after correcting the copied test-tree ownership. AppInspect first pass identified missing custom-config reload trigger and Cloud-only index sizing restrictions; both addressed. Python 3.13-only future requirement is incompatible with the 10.0 baseline and will be disclosed.
Goal-period progress added with RED→GREEN integration test; progress includes an explicit period and import as-of date.

Final review: fresh read-only reviewer found five Important correctness issues. Fixed with regressions: pace conversion, derivation-input revision identity, incomplete-distance endpoints, rejected-archive worker status, and per-metric validation (the latter gets installed SPL acceptance assertions). Parser version advanced so previous local snapshots cannot cache stale calculations.
Final review: re-graded unknown-effort baseline, GPX pace, pinned drilldown and calendar boundary findings as correctness rather than polish; corrected null ordering, observed GPX speed, snapshot-ID drilldown and configured-local calendar cutoff through import date. No deferred reviewer minors remain.
Final: Ruling: strengthen shared endpoint privacy by suppressing whole cells intersecting 200m endpoint-radius buffers, in addition to masking first/last 200m track samples — prevents coarse rounding from reintroducing endpoints; cost is deliberately reduced geography coverage.
Final: failed native startup after changing emulation was traced to root ownership of a test-created runtime parent, not app source. Corrected disposable directory ownership before restart.


Final runtime acceptance: Enterprise 10.0.11 indexes the private full export and selects its corrected latest snapshot without double counting. Enterprise 10.4.4 automatically ingests the synthetic ZIP using its bundled Python 3.13. Withheld telemetry leaves the old snapshot current; releasing it activates the edited/deleted replacement with current count unchanged. All 46 panel searches pass on both versions; all eight native pages render without errors on 10.0.11.
Final permissions acceptance: the built-in user role's wildcard grants were observed at runtime. Removed built-in inheritance from app roles and verified independent synthetic athlete/viewer/location users by direct searches, including a positive location sentinel. Existing broad roles remain an operator responsibility documented prominently.
Final time-filter regression: Splunk pre-evaluates invalid constant tonumber arguments in an unselected branch; changed numeric detection and sanitized conversion inputs, then proved all-time, relative and fractional epoch selections with real SPL. The verifier now uses completed job status, because export streaming omitted error details. Added regression tests for regex anchors and failed job detection.
Final review fixes: no deferred reviewer findings. Public deliverables omit personal source rows, activity statistics, locations, private screenshots, runtime credentials and raw exports.

Final retention regression: readiness markers now live in the historical data index, not the 90-day operations index. A RED→GREEN configuration contract ensures the active snapshot cannot disappear merely because operational logs age out.

## Annual trends in existing dashboards

Added annual activity counts and YoY changes by sport to Overview; yearly distance, weighted pace, explicit cadence conversion and coverage to Run Performance; and yearly skiing/sport moving speed and coverage to Gear and Sports. Annual panels support full history or comparable import-date YTD independently of Period. No new dashboard or ingestion schema was introduced.

Live Enterprise 10.4.4 validation: 55 installed panel searches, 17 hand-checked SPL fixture cases, three updated browser views, 40 local tests, deterministic package, and AppInspect with zero current errors/failures. See validation.md for test boundaries and the concurrency observation.
