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

The accompanying AppInspect report was generated with version 4.3.1 in precert mode. It has **zero errors and zero failures**. One future-failure finding requests a Python 3.13-only scripted-input declaration. The app deliberately retains its Python 3.9-compatible declaration for Enterprise 10.0; setting a mandatory 3.13 runtime would break that baseline. Runtime tests also cover Enterprise 10.4's Python 3.13.

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
