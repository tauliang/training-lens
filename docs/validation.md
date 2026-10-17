# Training Lens validation

The release was tested on Splunk Enterprise **10.0.11** and **10.4.4**, using isolated Linux containers. This is evidence for those versions, not certification of every 10.x minor or a clustered deployment.

| Check | Result |
|---|---|
| Python unit/integration suite | 40 tests passing on local Python 3.13 and Splunk 10.0's bundled Python 3.9 |
| Full private export | Strict FIT CRC decoding; source summary totals, samples and laps match the independent analysis baseline; no quarantined streams |
| Baseline installed dashboard searches | All 46 original panel searches pass strict search-job error checks on both tested Enterprise versions |
| Browser | All eight Studio pages render without query errors or JavaScript page errors on 10.0.11 |
| Quality modes | Real SPL fixtures prove that distance and duration guards are independent, with paired validity for pace |
| Scheduled input | 10.4.4's bundled Python 3.13 imported a synthetic ZIP after stable observations; native scheduled reconciliation activated it |
| Partial indexing | Withheld replacement telemetry left the previous snapshot active |
| Replacement snapshot | Releasing telemetry activated the replacement automatically; deleted activity disappeared from current totals and counts did not double |
| Access roles | Synthetic users prove athlete cannot read location index, viewer cannot read health/location indexes, and location role can read the synthetic location sentinel |
| Historical time | Multi-year source events retain original `_time`; current corrected snapshot selection and totals verified |
| Configuration | Enterprise 10.0 `btool check` reports no invalid configuration keys |
| Package | Deterministic `.spl`; source allowlist excludes exports, runtime data, credentials and caches |

Private reports, source rows, screenshots and temporary credentials are intentionally excluded from Git. The generic read-only verifier can reproduce installed panel-query checks against another test instance. It uses completed search jobs and inspects their error messages; the streaming export endpoint can otherwise return an empty stream for failed searches.

## AppInspect

The accompanying AppInspect report was generated with version 4.3.1 in precert mode. The current 1.0.1 package has **zero errors, zero failures and zero future failures**. Its scripted input declares `python.required = 3.13`; Enterprise 10.0 documents that key as a no-op, while later versions use it for compatibility. `python.version = python3` preserves the baseline interpreter selection and all app code is tested on Python 3.9 and 3.13.

Remaining warnings relate to scripted inputs, the one-minute reconciliation schedule, Cloud-specific metadata/config replication expectations, and legacy Python compatibility advice. Training Lens targets a single Splunk Enterprise instance, not Splunk Cloud. See `dist/appinspect-report.json` for the exact findings against the packaged artifact.

## Performance and limits

On the local emulated test host, ordinary full-history panel searches completed in roughly two seconds or less in the measured run. Full reconciliation across retained snapshots was slower, around eighteen seconds. These are observations on the test dataset and host, not latency guarantees. Administrators can reduce reconciliation frequency in `local/savedsearches.conf` if background cost matters more than activation delay.

The first QEMU-based test crashed the native Splunk indexer. Rosetta-based containers completed runtime acceptance. A subsequent test-only ownership and directory-copy error was corrected before the final run; neither changes the supported Linux deployment target.

Existing wildcard index permissions remain an administrator responsibility: Splunk role grants are additive. The supplied custom roles have no built-in wildcard inheritance, but adding one to an already broadly privileged user cannot remove that user's existing rights.

Optional features outside this release remain documented in the installation guide: proprietary load-model parity, measured-power inference, community leaderboards, API synchronization, custom calendar/route-matching components and automatic shared-dashboard publication.

## Annual trend update — 2026-10-17

Nine panels were added within Overview, Run Performance, and Gear and Sports. The dashboard count remains eight. The original 10.0.11 baseline was not rerun for this update; fresh runtime evidence is on Enterprise **10.4.4**.

- 40 unit/integration tests pass on local Python 3.13.
- All **55 installed panel searches** pass strict job-error checks against 219 synthetic workouts spanning 2022–2026.
- **17 live SPL fixture checks** validate annual sport counts, zero-activity years, year-over-year zero denominators, duration/distance weighting, MPH/km/h, min/mile/min/km, both cadence conventions, unconfirmed units, coverage, missing-year gaps, comparable YTD, gear/sport filters and escaped hostile filter text. Reproduce with `tools/verify_historical_trends.py`.
- All three changed dashboards render in Chrome without dashboard definition errors, SPL error text, or JavaScript page errors. Synthetic screenshots are in `screenshots/demo/*_annual.png`.
- The rebuilt package passes AppInspect 4.3.1 precert with zero errors and zero current failures; the existing Python runtime future finding and seven warnings remain. `dist/appinspect-report.json` was regenerated for this package.

The first all-panel API run overlapped with browser searches and reached the disposable instance's ten-concurrent-history-search limit (HTTP 503). Running verification separately passed every panel. Dashboard requests were queued by Splunk and rendered. Budget search concurrency for larger deployments; no global limits were changed.

Cadence normalization deliberately starts unconfirmed. Users choose the CSV convention before the steps/minute chart renders. Skiing charts measure whole-activity moving speed, including recorded lift/traverse movement, rather than a descent-only metric. Coverage counts accompany the annual trends.

## Social and Vitals — 2026-10-17

The app now has ten dashboards and 77 panel searches. Fresh validation on Enterprise **10.4.4** passed all 77 installed searches, all 47 Python unit/integration tests, and eleven synthetic live-SPL calculation/empty-state checks via `tools/verify_social_vitals.py`. Two synthetic source exports verified accepted/pending/mutual counts, observed net follower growth of +2, and top-follower interaction counts of 3 and 2, excluding a non-follower. Both new browser pages rendered without definition/SPL text errors or JavaScript page errors. The private export parsed successfully; its records and outputs were not published.

A structural scan of all FIT files found no standard max-MET/VO2 max (229) or HRV (78) messages. Incidental VO2 byte matches were decoded and contained no developer field descriptions. The CSV has no VO2 max column. This supports reporting no usable VO2 max for the supplied archive; proprietary unknown fields are not interpreted. Exercise HR and activity-associated athlete-weight values are supported. Weight units are left as exported.

The new `social` sourcetype is included in expected snapshot counts and reconciliation groups. Observations use only ready snapshots, with a no-ready sentinel. Missing native incoming interaction data is marked unavailable and never interpreted as zero follower engagement. Native archive contribution records have no actor identities for an incoming ranking.

The final rebuilt package passes AppInspect precert with zero errors/failures, the existing Python-runtime future finding and seven warnings. Testing initially created a parent runtime directory with root ownership before first startup; correcting ownership allowed clean startup. This was isolated test setup, not a package configuration change. No fresh 10.0 runtime run was performed for these additions; Python remains compatible with 3.9 and the prior baseline is documented above.

## Parameterized release — 2026-10-17

Current inventory: **10 routes, 28 panels**, replacing 77 separate panels. Native lookup inputs, smart result tokens and aggregated chain searches run on **Enterprise 10.0.11 and 10.4.4**. Both versions passed **384 completed-job checks** each: six independent calculation/null fixtures, 95 generated sources, 252 available metric × unit × grain combinations and 31 investigation-table modes. The synthetic dataset contains 219 activities and two observed social snapshots. Mode checks assert expected nonempty investigations, rather than accepting empty jobs as success.

The independent compiled-pipeline fixtures produce 145 bpm for unequal-duration HR, 25 MPH for unequal-duration speed, 175 steps/min after explicit stride conversion, peak180bpm, unchanged74 original-unit median weight, and null zero-denominator speed. The original annual/Social/Vitals regression fixtures remain available as reference checks against the preserved search inventory; the selector verifier additionally exercises the new generated pipelines.

The generated source inventory has **45 independent base jobs** across all ten pages, compared with77 previously; options/metadata/chart chains reuse bounded aggregated results. A page has1–6 independent jobs. Main-index chart searches are selected-metric-only; inactive table modes use an impossible indexed event-ID predicate. No concurrency limit was raised. API measurements and browser passes use disposable local containers, and are not production latency guarantees.

Effective ACL checks on10.4.4 confirm athletes can read private availability but cannot overwrite it; the sanitized viewer cannot read it. Header-only cache seeds and admin-only writes are packaging invariants. Ready-only cache refresh uses revision aggregates with expansion and reconciliation guards; stale/pending statuses remain explicit.

The main index is `strava`, with separate `strava_private`, `strava_shared`, `strava_ops` indexes. Package metadata is **1.0.0 · Tau Liang**. AppInspect precert reports0errors,0failures,0futurefailures,7warnings (Enterprise-only scripted-input/Cloud deployment advice). See the exact packaged report in `dist/appinspect-report.json`.

Folder-drop regression covers two stable observations, identical bytes under another filename, a future export with an added/reordered activity, unchanged spool contents on repeat, unique immutable telemetry event IDs, and retained summary versions. A failing regression initially found6physical sample records for4unique IDs; flushing telemetry chunks at revision boundaries fixes the duplicate emission. Runtime manifests/checkpoints are part of this idempotence contract and must be preserved.


Final browser acceptance on both versions covers all ten routes with no definition/SPL text errors or JavaScript page errors. Explicit bookmark cases on10.4.4 verify skiing MPH, confirmed running steps/min, average+peak HR legends, unchanged weight units under Imperial, invalid metric IDs and missing snapshots. Current synthetic screenshots replace the ten primary images in `screenshots/demo/`; older annual/detail images document previous layouts. The updated cache readiness and separate Training-zone series also pass targeted completed-job checks after review.

63 unit/integration tests pass on Python3.13 and Enterprise10.0's Python3.9. The final independent review found no remaining release blocker. Prior mixed-revision spool files are not retroactively rewritten; logical event-ID deduplication preserves totals, but an existing pre-release runtime may physically re-emit some telemetry once after the chunk layout changes.


The local API probe median was0.165seconds across95 current data-source checks (maximum0.719s), versus0.149seconds across77 prior panel checks (maximum0.243s). Expanded API chain checks are independent jobs, whereas the browser reuses base results; these timings do not establish an end-to-end speedup. The verified reduction is45independent page bases versus77previously. Browser runs completed without observed search failures and global concurrency settings were unchanged.


The native scheduled inbox worker on10.0.11 imported a dropped219-workout ZIP, processed an identical alias without another snapshot, then imported an overlapping/reordered220-workout ZIP. Scheduled reconciliation activated220activities with220distinct activity IDs. Physical snapshot manifests increased from the two fixture baselines to four, exactly one for each distinct dropped export; the renamed copy added none. No import CLI or forged ready event was used in this acceptance run.


## Release 1.0.1

Set `[package] check_for_updates = true` in app.conf and bump both launcher/id versions to1.0.1. The package builder derives its default output name from app metadata, and CI targets the new package. The metadata regression test now requires enabled update checks. All63local tests pass; the actual tar.gz was inspected to verify its flag/version/author and passes AppInspect with zeroerrors, failures or futurefailures. The superseded1.0.0GitHubrelease/tag will be removed after1.0.1 is published. The current precert report has8advisory warnings, including its private-app recommendation to disable update checks; update checks intentionally stay enabled to meet the requested validation requirement.
