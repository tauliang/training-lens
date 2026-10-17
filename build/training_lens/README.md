# Training Lens

Private training analytics from Strava exports, for Splunk Enterprise 10.x on a single Linux instance. Dashboard Studio pages cover training volume, imported effort, running performance, activity traces, geography, gear and data quality. No API account connection is required.

## Install and enable

Install `training_lens-1.0.0.spl` through Splunk Web, then restart Splunk. The app's script input is initially disabled. Create `local/inputs.conf` in the installed app:

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

The default period is the past year. Choose All time for older activity history. Snapshot defaults to latest; paste a ready snapshot ID from Data Health to pin a historical export. Activity rows link to detail dashboards, or enter a numeric activity ID directly. Gear is an exact-name filter or `All`.

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

Activity samples exclude raw latitude and longitude. Geography uses coarse cells after automatic masking of exported privacy zones and the first/last 200 meters of recorded tracks. Cells intersecting protected areas are conservatively suppressed. No address or geocoder request is indexed/sent. Exact GPS is off by default; enabling it sends raw points to the separately restricted `training_lens_private` index, accessible only to admin and users assigned `training_lens_location`. Masks affect new derived data, not previously indexed locations. Remove old data through your administrator's retention/purge procedures if needed.

`training_lens_viewer` can search sanitized geographic cells in `training_lens_shared`, but private dashboards are restricted to athlete/admin. Do not grant the athlete role merely to share a chart. The included geography dashboard uses private current membership; a separate shared dashboard and membership publisher are not part of this private release.

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

Overview includes annual counts and year-over-year activity changes by sport. Run Performance includes annual distance, distance-weighted pace, duration-weighted cadence and coverage. Gear and Sports includes yearly skiing speed, speed by sport and coverage. The app still has eight dashboards.

Annual panels use all years in the selected snapshot, independent of Period; Sport and Gear still apply. The annual comparison selector switches between Full years (latest year can be incomplete) and Comparable YTD through the import calendar date. Coverage tables count excluded or missing metric observations; absent cadence/speed is never zero-filled. Activity count charts include inactive calendar years between the first and last observed years; growth from zero has no percentage. The annual metric calculations always require valid durations and, for speed/pace, valid distances, including in Reported mode.

Set CSV cadence convention in Run Performance after checking the source: Strides/min × 2 or Steps/min × 1. Unconfirmed is the default, so the normalized chart starts empty. This choice affects the annual summary chart, not raw device cadence in Activity Detail. The exported activity mean is weighted by its recorded moving duration, which approximates cadence over covered activities, not measured time at each step. If historical sources use different conventions, normalize them before applying one convention to the selected history.

Speed uses summed distance / summed moving time within each sport/year, in MPH or km/h. Skiing summaries include recorded lifts/traverses; the app does not claim downhill-only speed or infer peak speed from averages. Metric lines have gaps for years without a measurement.
