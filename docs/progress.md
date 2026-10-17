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
