# Training Lens architecture

The approved implementation targets offline personal training analysis in a single-instance Splunk Enterprise app. Names use `training_lens` consistently. The eight dashboard pages follow native Dashboard Studio patterns without a JavaScript build or external service dependency.

## Ingestion

The scheduled Python worker observes ZIP size and mtime over at least 60 seconds. Archive validation rejects unsafe names, duplicate members, symlinks, encryption, unsupported schema and decompression limits. Members are read in memory with bounds; nothing is extracted or executed.

CSV headers retain occurrence suffixes, preserving all duplicated metrics. Detailed distance is meters; UTC dates retain source provenance. The parser distinguishes null from zero and derives metric-specific quality flags. An explicit Filename reference maps each summary to its FIT/GPX member.

A snapshot identity hashes archive content, parser version and configuration. Stream identities hash original member bytes, athlete/activity identity, parser version and derived configuration. The importer writes immutable content-addressed NDJSON chunks using fsync and atomic rename, then records a local manifest. Indexing completion is a separate state.

FIT CRC validation is strict. Invalid streams are quarantined without erasing valid CSV summaries. Standard FIT coordinates convert from semicircles to degrees, enhanced speed/altitude take precedence, and GPX supports UTF-8 namespaces and common HR/cadence extensions. Unknown fields remain ignored rather than becoming arbitrary indexed data.

## Indexes and readiness

- `training_lens`: activity summaries, memberships, sample telemetry without location, laps, derived metrics and durable readiness markers.
- `training_lens_private`: opt-in exact location samples, with a separate role.
- `training_lens_shared`: coarse geographic cells produced after endpoint and protected-zone masks.
- `training_lens_ops`: worker status with shorter operational retention.

Reconciliation collapses logical groups by snapshot or stream revision and counts distinct event IDs. Snapshot manifests supply expected summary counts; memberships supply expected telemetry counts. A snapshot becomes ready only when all its groups match. Readiness is published as a single immutable marker instead of mutable registry lookups. Current searches select the ready snapshot with the newest import epoch; telemetry searches restrict to its stream membership. Empty ready/membership selections fail closed. Repeated physical events cannot double logical totals.

Older snapshots remain available by ID, including their original quality and correction state. New full exports can delete or edit activities without stale membership leaking into current totals. Config changes rebuild derived state. Index retention preserves historic event time within the configured age and disk-size limits.

## Analysis and privacy

Zone durations use adjacent observed HR intervals, split at timer events; gaps over 30 seconds and missing HR remain unobserved. No duration is extrapolated beyond the final sample. Confirmed effective-dated zone boundaries are required.

Best efforts evaluate continuous monotonic distance-time segments and interpolate start/end crossings. Gaps, distance resets and implausible jumps break continuity. Device laps remain distinct from kilometer splits. Pace aggregates use sums of the same valid distances and durations, not the mean of per-activity pace.

Personal geography counts one visit per activity/cell after the first and last 200 meters and exported privacy zones are removed. Entire cells touching protected regions are suppressed conservatively. Raw samples never carry coordinates. Exact points can be retained only by opt-in in a separately restricted index. Existing indexed locations require administrative retention/purge if masks change.

The native dashboards use quoted SPL tokens and validated numeric activity IDs. Display labels never become executable search fragments. Personal notes, messages, email, birth date, login history, social graphs, media and privacy-zone addresses are excluded from indexing.

## Release boundaries

The first release includes native charts/tables and a bubble map with an offline table fallback. It does not implement community segment rankings, proprietary load parity, inferred power-duration curves, API sync, custom calendar components or route matching. Those need additional data or separate requirements. Goal progress is explicitly as of import date rather than a live estimate. Automatic geo sharing to other users requires a separate sanitized membership publisher; athlete/admin dashboards remain private.
