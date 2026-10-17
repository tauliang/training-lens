# Training Lens

A private Splunk Enterprise app for analyzing Strava data exports. Import your ZIP locally and explore training volume, imported Relative Effort, running performance, heart rate, activity details, geography, equipment and data quality.

## Install

Install [`dist/training_lens-1.0.0.spl`](dist/training_lens-1.0.0.spl) through Splunk Web and follow the [installation and configuration guide](build/training_lens/README.md). Enable the disabled script input, assign the athlete role, and copy exports into the private inbox. A scheduled reconciliation search switches dashboards only after indexing completes. The main ingestion index is `strava`.

The app runs without Strava API credentials or an external database. Exact GPS import is off by default. Personal ZIPs, normalized data, preferences and runtime credentials are excluded from the repository and release package.

## Dashboards

| Page | Purpose |
|---|---|
| Overview | Recorded volume, annual activity counts and changes by sport, consistency and recent activity |
| Training | Weekly log, imported effort, custom HR zones and configured goal progress |
| Run Performance | Weekly and annual distance/weighted pace, yearly cadence and app-derived best efforts |
| Activity Detail | Time-aligned HR, pace, elevation, raw cadence, laps, splits and strength details |
| Geography | Privacy-masked activity visits to coarse geographic cells |
| Gear and Sports | Equipment usage, yearly skiing/sport speed trends and metric coverage |
| Vitals | Exercise HR, peak HR, HR-zone and recorded-weight history, with measurement coverage |
| Social | Observed follower growth, given/received engagement, current-follower rankings and coverage |
| Data Health | Indexed readiness, source quality, stream coverage and import status |
| Setup | Configuration instructions, source settings and import manifests |

Annual panels use the full selected snapshot and the Sport/Gear filters, independently of Period. Choose **Full years** (the latest year may be partial) or **Comparable YTD** to compare through the import calendar date. Overview fills inactive years within the observed history with zero counts and leaves percentage growth undefined when the previous count is zero. Metric gaps remain missing.

In Run Performance, choose the **CSV cadence convention** to enable the annual steps/min chart: `Strides/min` doubles the exported value; `Steps/min` preserves it. The default `Unconfirmed` leaves normalized cadence blank. Confirm the convention against the recording source. Cadence uses moving-duration-weighted activity averages over runs with cadence; it does not infer values for uncovered runs. Pace is computed from total valid time/distance. Speed is total valid distance/time for each sport, shown in MPH or km/h; skiing speed includes lifts/traverses wherever those are counted in the exported totals and is not a downhill-only measurement.

Missing metrics remain missing. Source conflicts are visible. Imported average power does not fabricate a measured power stream, and the app does not claim parity with Strava's proprietary fitness calculations or community leaderboards.

## Development

```sh
python -m unittest discover -v
python tools/generate_dashboards.py
python tools/package.py
```

Source lives in `build/training_lens/`; generated Dashboard Studio XML lives under its default views directory. The package builder uses an allowlist and deterministic timestamps. CI tests Python 3.9 and 3.13, checks dashboard generation drift and uploads installable artifacts.

Use the [read-only Enterprise verifier](tools/verify_enterprise.py) against a test installation, with `SPLUNK_TEST_PASSWORD` supplied through the environment:

```sh
python tools/verify_enterprise.py --url https://localhost:8089 --expected-activities 10 --output /private/path/results.json
```

Run `python tools/verify_historical_trends.py --url https://localhost:8089 --output /private/path/history-results.json` with the same credentials to execute the generated annual panel searches against synthetic in-memory fixtures. This verifies weighted calculations, cadence conventions, missing-year gaps, YTD, zero denominators and filter escaping without indexing data.

TLS verification is on by default. `--insecure-local-test` is restricted to localhost and intended only for isolated disposable instances. See [implementation record](docs/progress.md) and [validation status](docs/validation.md) for measured coverage and release limits.

## Scope

Single athlete, single Linux instance, Splunk Enterprise 10.x. Distributed ingestion, API synchronization, custom route matching/calendar components and modeled Fitness & Freshness are outside this release. Set custom HR boundaries before expecting zone results. Dates are UTC instants with configurable IANA reporting timezone. The included role and index layout keeps raw health/location data private; a separately published shared dashboard is not included.

Apache-2.0, with a bundled MIT-licensed FIT decoder. This independent project is not affiliated with Strava or Splunk.

The baseline was validated on Enterprise **10.0.11** and **10.4.4**. The annual trend update passed 40 tests, all **55 installed panel searches** and **17 calculation/edge-case checks** on **10.4.4**, with browser validation of the three changed dashboards. Baseline snapshot lifecycle and eight-page browser checks are documented in the validation report. AppInspect has zero current errors/failures; its Python 3.13-only future declaration finding is documented in the validation report because the app also supports Enterprise 10.0's Python 3.9 runtime.

## Social data

The native archive supplies follower/following snapshots and your exported social contributions (comments and kudos given). It does not supply follow dates or the identities/timestamps of people interacting with your activities. Social shows observed follower counts across distinct imported exports, not reconstructed historical follows. One export gives one baseline. Its date is the import observation time, not the original relationship date or the date the export was generated.

Comments/kudos received and top-current-follower rankings work when an optional `social_interactions.csv` is included with the ZIP; otherwise an availability panel identifies the missing data. See the [social import contract](build/training_lens/README.md#social-dashboard) for fields and limitations. Comment text and athlete names are not indexed. Reimport exports after upgrading to populate these new records.

## Vitals data

Vitals defaults to All time and includes monthly/yearly exercise heart-rate trends by sport, recorded activity peaks, annual HR-zone hours, and recorded athlete-weight values associated with activities. Exercise HR is weighted by valid moving duration, not averaged equally across short and long workouts. Coverage counts accompany the trends. Weight retains original export units and is not presented as a dated weigh-in.

The supplied archive has exercise HR and recorded weight, but no standard VO2 max or HRV messages were found across its FIT files and no VO2 max column exists in activities.csv. The dashboard does not estimate VO2 max, resting HR or HRV from workout averages.

Social/Vitals validation: **47 tests**, **77 installed panel searches** on Enterprise **10.4.4**, eleven additional live calculation/empty-state checks, two-snapshot social checks and both new browser views. Run `tools/verify_social_vitals.py` with the same connection arguments and credential environment as the other Enterprise verifiers. The package has been rebuilt and AppInspect regenerated.

### Parameterized dashboards

The 10 dashboards now use **28 panels**, with lookup-backed metric, sport, gear, configured-goal and best-effort target choices. Metric selection changes values, legends and axis units together. The catalog includes volume, sport performance, confirmed running cadence, HR/weight, telemetry and social metrics; unavailable measurements remain explicit. See the [configuration guide](build/training_lens/README.md#parameterized-panels-and-lookup-maintenance) for cache status and upgrade instructions. Release metadata: **1.0.0 · Tau Liang**.
