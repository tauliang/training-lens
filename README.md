# Training Lens

A private Splunk Enterprise app for analyzing Strava data exports. Import your ZIP locally and explore training volume, imported Relative Effort, running performance, heart rate, activity details, geography, equipment and data quality.

## Install

Install [`dist/training_lens-1.0.0.spl`](dist/training_lens-1.0.0.spl) through Splunk Web and follow the [installation and configuration guide](build/training_lens/README.md). Enable the disabled script input, assign the athlete role, and copy exports into the private inbox. A scheduled reconciliation search switches dashboards only after indexing completes.

The app runs without Strava API credentials or an external database. Exact GPS import is off by default. Personal ZIPs, normalized data, preferences and runtime credentials are excluded from the repository and release package.

## Dashboards

| Page | Purpose |
|---|---|
| Overview | Recorded volume, sport mix, consistency, coverage and recent activity |
| Training | Weekly log, imported effort, custom HR zones and configured goal progress |
| Run Performance | Running distance, weighted pace and continuous app-derived best efforts |
| Activity Detail | Time-aligned HR, pace, elevation, raw cadence, laps, splits and strength details |
| Geography | Privacy-masked activity visits to coarse geographic cells |
| Gear and Sports | Recorded equipment usage and sport-specific summaries |
| Data Health | Indexed readiness, source quality, stream coverage and import status |
| Setup | Configuration instructions, source settings and import manifests |

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

TLS verification is on by default. `--insecure-local-test` is restricted to localhost and intended only for isolated disposable instances. See [implementation record](docs/progress.md) and [validation status](docs/validation.md) for measured coverage and release limits.

## Scope

Single athlete, single Linux instance, Splunk Enterprise 10.x. Distributed ingestion, API synchronization, custom route matching/calendar components and modeled Fitness & Freshness are outside this release. Set custom HR boundaries before expecting zone results. Dates are UTC instants with configurable IANA reporting timezone. The included role and index layout keeps raw health/location data private; a separately published shared dashboard is not included.

Apache-2.0, with a bundled MIT-licensed FIT decoder. This independent project is not affiliated with Strava or Splunk.
