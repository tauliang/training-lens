# Training Lens validation

The release was tested on Splunk Enterprise **10.0.11** and **10.4.4**, using isolated Linux containers. This is evidence for those versions, not certification of every 10.x minor or a clustered deployment.

| Check | Result |
|---|---|
| Python unit/integration suite | 40 tests passing on local Python 3.13 and Splunk 10.0's bundled Python 3.9 |
| Full private export | Strict FIT CRC decoding; source summary totals, samples and laps match the independent analysis baseline; no quarantined streams |
| Installed dashboard searches | All 46 panel searches pass strict search-job error checks on both tested Enterprise versions |
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
