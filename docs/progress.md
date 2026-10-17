# Implementation ledger

Plan: Training Lens implementation, authorized October 17, 2026.

Pre-flight: summary Activity → importer → snapshot manifest → native dashboard searches; signatures will be pinned in tests. Stream revision → derived intervals → membership filter is the second shared interface. Packaging consumes generated dashboards and vendor allowlist.

Ruling: app ID and field prefix are training_lens / tl, as named by the user after the design; rename cost is mechanical.
Ruling: use a separate clone and feature branch for the target repository; preserve the unrelated workspace and all personal data outside Git.
Ruling: publish a reconciled immutable ready event rather than mutable CSV registry files. A single marker contains the snapshot identity and import order; all current activity and stream membership searches resolve that marker. This avoids partially published filesystem lookups and requires no management credentials. Cross-panel dispatch can straddle an activation; explicit snapshot selection pins a review session.

## Tasks

- [ ] 1 Canonical parser and quality rules
- [ ] 2 Safe archive lifecycle and deterministic spool
- [ ] 3 Splunk input and reconciliation
- [ ] 4 Native dashboards
- [ ] 5 FIT and GPX decoding
- [ ] 6 Derived intervals, best efforts, geography
- [ ] 7 Package, compatibility validation, review and push

Task 1: complete — 7 parser tests RED (empty stub) → GREEN; private full-export count, SI distance, duration conflicts and effort disagreements matched independently measured baseline. No personal data stored in repository.

Task 2: complete — archive/lifecycle RED→GREEN, 12 tests pass. Root cause of the recovery assertion was missing notification of repaired chunks, corrected by comparing the prior manifest before rebuilding. Stable scans, content hashes, bounded nested decompression, explicit errors and independent snapshots covered.

Task 3: native config and reconciliation contract implemented; runtime acceptance pending. Logical groups reconcile distinct event IDs; duplicate physical events do not inflate counts.
Task 5: decoder RED→GREEN with synthetic FIT CRC and timestamp fixture, GPX extensions, coordinates, truncation and rejected XML declarations. Full private archive validation running.
Task 6: derived analysis RED→GREEN (HR intervals/pauses/gaps, interpolated best efforts, distance resets and privacy). Export privacy-zone masking has an independent integration fixture that failed with three leaked cells before the automatic exported-zone mask was added; now zero shared cells. Raw sample events never carry location.
Ruling: use only confirmed custom HR zones. Until configured, HR traces remain usable and zone panels explain missing configuration; do not silently treat the old exported maximum HR as current.

Task 4: eight native Dashboard Studio pages generated; filter tokens use SPL string escaping, empty snapshot selection fails closed, activity IDs are validated, and detail queries are bounded by current stream membership. Generator/package tests RED→GREEN. Browser and runtime SPL checks pending.
