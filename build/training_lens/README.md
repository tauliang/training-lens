# Training Lens

Private training analytics from Strava exports, for Splunk Enterprise 10.x on a single Linux instance. Dashboard Studio pages cover training volume, imported effort, running performance, activity traces, geography, gear and data quality. No API account connection is required.

## Install and enable

Install `training_lens-1.0.1.spl` through Splunk Web, then restart Splunk. The app's script input is initially disabled. Create `local/inputs.conf` in the installed app:

```ini
[script://./bin/import_strava.py]
disabled = 0
```

Set reporting preferences in `local/training_lens.conf`:

```ini
[settings]
athlete_id = personal
timezone = America/New_York
decode_streams = true
```

Assign `training_lens_athlete` as the intended user’s sole search role. Admin also has access. Splunk index grants are additive: built-in `user` and other existing roles may allow `*`, which includes these indexes. Review and remove wildcard grants for anyone who must not see health/location data; adding an app role cannot revoke permissions from other roles. The supplied athlete/viewer roles deliberately do not inherit the built-in wildcard role. Restart Splunk after enabling/configuring the input. The worker creates this private inbox, owned by the Splunk service account:

```text
$SPLUNK_HOME/var/lib/training_lens/inbox/
```

Copy a completed Strava ZIP into it. The worker waits for two stable observations at least 60 seconds apart, creates normalized spool files, and leaves original ZIPs in place. Splunk monitors completed JSON chunks; the scheduled reconciler activates imports only after distinct indexed counts match every manifest group. This can take several minutes. Use Data Health to inspect progress. No manual "ready" event is needed.

New exports replace current membership instead of doubling historical totals. Summary and telemetry content have deterministic IDs; unchanged streams are reused across exports. Physical duplicate events from retries are deduplicated by searches. No automatic deletion of raw spool files is performed; keep them for recovery or archive them only after verifying indexed readiness and backups.

The default period is the past year. Choose All time for older activity history. Snapshot defaults to latest; paste a ready snapshot ID from Data Health to pin a historical export. Activity rows link to detail dashboards, or enter a numeric activity ID directly. Sport and Gear are lookup-backed dropdowns derived from the selected ready snapshot.

## Zones, privacy, goals and corrections

Create an admin-owned `config.json` in `$SPLUNK_HOME/var/lib/training_lens/` before importing or rescanning an export:

```json
{
  "exact_gps": false,
  "gear_thresholds": [{"gear": "Daily trainers", "distance_m": 600000}],
  "hr_zones": [
    {"effective_date": "2026-01-01", "boundaries": [120, 140, 160, 175]}
  ],
  "goals": [
    {"sport": "Run", "metric": "distance_m", "target": 100000, "period": "month"}
  ],
  "overrides": [
    {"activity_id": "123", "field": "distance_m", "value": "5000", "reason": "Device correction", "revision": "1"}
  ]
}
```

The zone numbers above are illustrative custom boundaries; set your own. No age-based maximum HR or proprietary fitness score is assumed. Without configured zones, HR traces remain available but zone panels are empty. Boundaries apply from the latest effective date on or before each activity. Zone durations do not interpolate across gaps over 30 seconds or timer pauses.

Goal metrics: `distance_m`, `moving_time_s`, `activity_count`, `elevation_gain_m`. Goal progress uses validated source measures in the calendar week/month/year through the import date, labeled with its period start and as-of date. Corrections preserve source history in older snapshots. Correctable fields: distance, moving/elapsed time, elevation, effort, average HR, gear and sport. Config changes produce a new snapshot and recompute derived analysis.

Activity samples exclude raw latitude and longitude. Geography uses coarse cells after automatic masking of exported privacy zones and the first/last 200 meters of recorded tracks. Cells intersecting protected areas are conservatively suppressed. No address or geocoder request is indexed/sent. Exact GPS is off by default; enabling it sends raw points to the separately restricted `strava_private` index, accessible only to admin and users assigned `training_lens_location`. Masks affect new derived data, not previously indexed locations. Remove old data through your administrator's retention/purge procedures if needed.

`training_lens_viewer` can search sanitized geographic cells in `strava_shared`, but private dashboards are restricted to athlete/admin. Do not grant the athlete role merely to share a chart. The included geography dashboard uses private current membership; a separate shared dashboard and membership publisher are not part of this private release.

## Data rules and limitations

CSV duplicate headers are preserved by occurrence. Detailed meter-valued distance and second Relative Effort are canonical; disagreements are flagged. Invalid or conflicting measurements remain available in Reported mode; Validated mode applies metric guards. Running pace uses aggregate seconds divided by the same rows' aggregate distance. Zero-distance strength records retain time and HR.

FIT CRC failures and malformed files quarantine that stream, while its valid CSV summary remains available. GPX must be UTF-8 and contain explicit timezone timestamps; XML DTD/entity declarations are rejected. No export member is executed or extracted. Limits: ZIP 2 GiB, outer expansion 4 GiB, decoded activity aggregate 4 GiB, decoded member 128 MiB, 20,000 members, compression ratio 200:1. Unsafe paths, duplicate ZIP names, symlinks and encrypted members are rejected.

Device laps and generated kilometer splits are distinct. Best efforts use continuous cumulative distance and elapsed timestamps; gaps, resets and implausible jumps break continuity. Average power alone does not yield measured power curves, normalized power or FTP stress. Routes, community leaderboards, Strava's proprietary fitness algorithms and API sync are not reconstructed.

The app currently supports one athlete per instance. UTC instants are retained; reporting dates use the configured IANA timezone. The CSV schema's date strings are interpreted as UTC, with stream timestamps preferred where available. Unknown export schemas fail rather than guessing units.

Indexes retain activity history for 30 years by age, subject to inherited or locally configured index size caps. Operations retain 90 days. Administrators must size storage before import: size caps can freeze old records even within the age window. Set explicit `maxTotalDataSizeMB` values in `local/indexes.conf` appropriate for the instance. Do not enable the input until sufficient disk and license capacity are available. Detailed JSON can be much larger than the compressed archive. This is a single-instance app; clustered input coordination is not implemented.

## Troubleshooting and rollback

- No worker status: confirm the script input is enabled, executable and owned by Splunk; inspect `splunkd.log` and scheduled-search permissions.
- Import emitted but not active: compare Data Health manifests and group counts; confirm spool monitors and all four indexes are enabled. Some telemetry may still be indexing.
- Failed worker: source values are omitted from logs deliberately. Validate the ZIP locally with the CLI; unsupported/corrupt files are quarantined or rejected with a category.
- Empty recent panels: select All time and check the active snapshot, sport, gear and quality filters.
- Empty zones: configure confirmed boundaries and reimport/rescan. Empty best efforts can mean no valid continuous target-length interval exists.
- Offline maps: use the cell table. Basemap tiles may require network access; no online geocoding is used.

To pause imports, disable the script input. To roll back dashboards, reinstall the prior app package without removing `local/` settings or the runtime directory. Pin an older ready snapshot ID for historical review. The ready marker with the newest import epoch remains the automatic default; do not manually forge markers. Back up Splunk indexes and the runtime directory together.

## License

Apache-2.0 for Training Lens; fitdecode 0.11.0 is MIT licensed. See THIRD_PARTY_LICENSES and the bundled full license. Training Lens is independent and is not affiliated with Strava or Splunk.

## Annual history panels

Overview includes annual counts and year-over-year activity changes by sport. Run Performance includes annual distance, distance-weighted pace, duration-weighted cadence and coverage. Gear and Sports includes yearly skiing speed, speed by sport and coverage. These annual panels reuse the original dashboards.

Annual panels use all years in the selected snapshot, independent of Period; Sport and Gear still apply. The annual comparison selector switches between Full years (latest year can be incomplete) and Comparable YTD through the import calendar date. Coverage tables count excluded or missing metric observations; absent cadence/speed is never zero-filled. Activity count charts include inactive calendar years between the first and last observed years; growth from zero has no percentage. The annual metric calculations always require valid durations and, for speed/pace, valid distances, including in Reported mode.

Set CSV cadence convention in Run Performance after checking the source: Strides/min × 2 or Steps/min × 1. Unconfirmed is the default, so the normalized chart starts empty. This choice affects the annual summary chart, not raw device cadence in Activity Detail. The exported activity mean is weighted by its recorded moving duration, which approximates cadence over covered activities, not measured time at each step. If historical sources use different conventions, normalize them before applying one convention to the selected history.

Speed uses summed distance / summed moving time within each sport/year, in MPH or km/h. Skiing summaries include recorded lifts/traverses; the app does not claim downhill-only speed or infer peak speed from averages. Metric lines have gaps for years without a measurement.

## Social dashboard

The Social dashboard imports `followers.csv`, `following.csv`, `comments.csv` and `reactions.csv` when present. It displays accepted/pending followers, following, mutual connections, observed follower-count growth and changes, monthly contributions given, monthly received interactions from current followers, a top-current-followers table, a relationship roster and availability status. Social network history uses Period independently of the pinned Snapshot. Engagement and roster use the selected snapshot. Sport/Gear only scope the activity-derived choices, so leave them at All on Social.

Native archive comments/kudos are treated as contributions given, not as people engaging with your activities. Comment bodies, names, reaction parent IDs and social preferences are omitted. Follower IDs are stored in the athlete-restricted activity index. Optional files are not required for ordinary activity imports. Missing files produce unknown metrics, not a fabricated zero. CSV dates without offsets use the export's UTC convention; reporting uses the configured timezone.

No follow dates exist in the native roster. Growth uses import observations from all reconciled exports within Period, independently of Snapshot selection. Reimporting the identical archive under different settings is deduplicated by archive hash. One export is a baseline, not a growth history. Uploading older exports later does not reconstruct their original export dates; import them chronologically if you want the resulting observations to be useful. The latest roster is the selected snapshot's exported roster, which may already be stale.

To populate received-interaction panels, include a supplemental `social_interactions.csv` at the ZIP root, with this exact header:

```csv
Interaction ID,Interaction Date,Interaction Type,Actor Athlete ID,Activity ID
comment_1,2026-01-02T12:00:00Z,Comment,123,456
kudos_1,2026-01-03T12:00:00Z,Kudos,123,456
```

These are illustrative IDs, not records to import as real data. Dates require an offset for ISO timestamps (or the native UTC export date format); interaction types are `Comment` or `Kudos`. IDs must be unique within the supplemental file. Activity IDs must exist in the same export. Actor IDs must be numeric. The file must contain actual received events obtained separately; the app does not connect to Strava or infer identities from text. Rankings include only actors on the accepted follower roster in the selected snapshot, count comments and kudos equally, and honor Period. A follower's status at interaction time is unknown. Displayed IDs are athlete IDs because the native roster has no names.

Supply a complete desired received-interaction history with each replacement export: snapshot replacement removes old interaction rows from current totals just as it replaces activity rows. Rankings reflect only supplied records; an empty file does not prove no engagement occurred. Reimport the export on upgrade because importer version 1.0.3 emits social records and includes them in snapshot reconciliation. Old snapshots stay usable; new readiness waits for social indexing too.

## Vitals dashboard

Vitals uses activity-associated measurements and defaults to All time. It provides exercise-HR coverage, moving-duration-weighted average HR by month/year and sport, annual recorded maximum HR, configured HR-zone hours by year, and median recorded athlete-weight values by activity year. All heart-rate charts use bpm. Weight preserves original CSV units under either Units setting. The activity date is not asserted to be a weigh-in date.

Average HR must be positive and at most 255 bpm; time weighting also requires a positive, valid moving duration. Maximum HR uses the detailed CSV column where available, otherwise the summary Max Heart Rate column. Maximum values outside the supported range or below a reported activity average are omitted from peak charts. Coverage distinguishes activities with an average from those that also have usable duration for weighting. Source values remain visible in activity summaries.

HR-zone charts require configured boundaries and a reimport using importer 1.0.3; annual records use the configured reporting timezone. Effective-dated zone changes can affect comparisons across years. These are workout measurements, not resting measurements or clinical assessments. Different sports/intensities should be compared separately.

The supplied archive contains no standard FIT max-MET/VO2 max messages, no standard FIT HRV messages and no VO2 max column in the activity CSV. VO2 max, resting HR and HRV are explicitly listed as unavailable; this release does not estimate them. No generic FIT developer metric or proprietary field is inferred as VO2 max. Reimport on upgrade to emit recorded weight, maximum-HR fallback and annual HR-zone context.

## Parameterized panels and lookup maintenance

Version **1.0.1**, author **Tau Liang**. The main ingestion index is **`strava`**. Optional exact GPS uses `strava_private`, masked cells use `strava_shared`, and worker logs use `strava_ops`. App ID, sourcetypes and role names remain `training_lens`.

The ten dashboard URLs now contain 28 panels. Choose a metric to reuse its chart; labels, legends and axis units come from the same catalog definition. Time grain replaces weekly/monthly/yearly copies. The Overview summary aggregates the selected period directly. HR comparison overlays average and peak bpm; engagement overlays comments and kudos. Rate series retain sport when Sport=All, so skiing and running pace are not combined. Table-mode selectors retain investigation, coverage and operational workflows. Maps show an explicitly labeled top 1,000 cells.

An admin-owned static catalog defines supported metrics. Two searches refresh private availability and dimension CSV lookups every five minutes, using ready snapshots. No reimport is needed for this selector change. Existing source-dependent features still require records emitted by importer 1.0.3. Lookup files shipped in the package contain no athlete data; runtime caches have headers only.

Availability describes the complete snapshot, not the selected period. Automatic chooses the first available metric by catalog order. A bookmarked metric absent after a sport/snapshot change shows “Choose an available metric” and an empty chart. Missing cache for a newly ready snapshot is pending. After 15 minutes, old metric choices are marked “cache stale”; Data Health → Import readiness → Availability cache reports age/status. A chart with a valid choice and no eligible observations in the selected period remains empty.

Cache refresh aggregates telemetry per immutable revision before associating snapshots. Expansion cardinality guards and a reconciliation guard suppress publication on detected partial data; `override_if_empty=false` preserves the prior cache. Pending snapshots are excluded without blocking refresh of ready snapshots. Investigate scheduler/search warnings rather than increasing concurrency or memory limits blindly. General search-job finalization and administrative cancellation are monitored by Splunk scheduler logs; a CSV write alone is not a universal job-success certificate.

Lookup definitions/files are app-scoped: athletes can read, administrators can write; the sanitized viewer role cannot read these private caches. Keep scheduled refresh ownership with an administrator. Clustered deployment and multi-athlete use require separate design.

Upgrade from an earlier development build using `training_lens` indexes: new monitors/searches use `strava` and do not migrate old buckets. Reimport the original ZIP into the new indexes using a fresh runtime/spool checkpoint or perform an administrator-managed migration, then verify reconciliation before retiring old indexes. Do not merely rename bucket directories. Back up runtime state and indexes first.


## Repeat and future folder drops

After the one-time installation, role assignment, configuration and input enablement, copy ZIPs to `$SPLUNK_HOME/var/lib/training_lens/inbox/`. No per-export command or lookup edit is needed. The worker waits for two unchanged observations at least 60 seconds apart, then imports; reconciliation activates the new snapshot and the five-minute cache refresh supplies its selector choices.

Dropping the same bytes again, including under another filename, produces the same snapshot and no new spool chunks. Future overlapping exports preserve versioned summary records intentionally. Every dashboard selects one complete snapshot and deduplicates event IDs, so an activity appears once and corrections/deletions follow the selected export. Full snapshots are required; this is not an append-only delta-file importer. Unchanged telemetry uses deterministic revision IDs and revision-local chunks, even if activities are reordered or new activities appear first. Keep the runtime manifests and spool/checkpoint state when upgrading; deleting ingestion state or replaying sources manually can cause physical re-indexing outside the normal folder-drop contract.


Pre-release upgrade caveat: older mixed-revision spool chunks are not rewritten. A first later export can physically emit some unchanged telemetry once in the new chunk layout; deterministic event-ID deduplication still keeps dashboard totals unique. Clean1.0.0 installs use revision-local chunks from the first import.
