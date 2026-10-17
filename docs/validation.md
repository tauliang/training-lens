# Training Lens validation

Validation is in progress. Do not interpret the existence of a package as certification across all Splunk Enterprise 10.x minors.

- Local Python 3.13 unit tests cover summary parsing, archive limits, restart/reimport behavior, FIT integrity, GPX, derivations, privacy, dashboard references and deterministic packaging.
- The same suite has run under Splunk Enterprise 10.0's bundled Python 3.9; one initial test-tree ownership error was corrected and all then-current tests passed.
- A private full-export pass decoded all referenced streams with strict FIT CRC checks and matched independently measured CSV counts, distance, raw sample and lap counts. No source rows are committed here.
- Runtime indexing, installed dashboard searches, UI checks and final AppInspect status will be recorded after the disposable test deployment completes.
- Initial QEMU emulation crashed the Splunk indexer before runtime acceptance. The test deployment is being recreated with Rosetta to match the existing working local test environment.
