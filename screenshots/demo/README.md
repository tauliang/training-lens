# Training Lens demo screenshots

Captured from the native Training Lens dashboards running on Splunk Enterprise 10.4.4.

All screenshots use a generated dataset of 107 fictional workouts over 150 days: running, cycling, and strength training. Routes, heart rate, cadence, gear, effort, and goals are synthetic. No data from the personal Strava export is included.

- [Overview](overview.png)
- [Training](training.png)
- [Running performance](run_performance.png)
- [Activity detail](activity_detail.png)
- [Geography](geography.png)
- [Gear and sports](gear_sports.png)
- [Data health](data_health.png)
- [Setup](setup.png)

Images show the initial dashboard viewport at 1600 × 1500 pixels; additional panels are available by scrolling in Splunk. The Activity Detail screenshot has a fictional run selected.

## Annual trend panels

The following screenshots use a separate fictional dataset of 219 workouts spanning 2022–2026, captured in the existing dashboards with Imperial units and the cadence source convention explicitly set to Strides/min. These are scrolled views of the added annual sections.

- [Overview: annual counts and changes by sport](overview_annual.png)
- [Run Performance: annual distance, pace and cadence](run_performance_annual.png)
- [Gear and Sports: annual skiing and sport speed](gear_sports_annual.png)

## Social and Vitals

These screenshots use fictional measurements and two fictional imported network snapshots. Received interactions are supplied through the documented supplemental CSV; the personal export does not contain those actor-level records. Growth dates are synthetic import observations.

- [Vitals: exercise heart-rate history](vitals.png)
- [Vitals: zones, original-unit recorded weight and coverage](vitals_detail.png)
- [Social: network observations and source availability](social.png)
- [Social: given/received engagement and follower ranking](social_detail.png)


## Current parameterized release

The ten primary images (`overview.png`, `training.png`, `run_performance.png`, `activity_detail.png`, `geography.png`, `gear_sports.png`, `social.png`, `vitals.png`, `data_health.png`, `setup.png`) now show version1.0.0's28-panel layouts, captured at1600×1700 onEnterprise10.4.4. The data is fictional:219workouts spanning2022–2026 and two synthetic network observations. Default metrics use Metric units and unconfirmed CSV cadence. Every primary screenshot was refreshed after the parameterized implementation; `_annual.png` and `_detail.png` files retain earlier layouts for reference.
