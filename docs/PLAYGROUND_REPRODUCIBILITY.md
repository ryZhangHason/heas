# Playground Reproducibility Notes

## Determinism Contract
- Determinism depends on fixed `seed`, identical config payload, and same runtime versions.
- `config_hash` is generated from the serialized V2 config payload.
- `run_id` is timestamp + config hash suffix for traceability.

## Artifact Format
Publication bundle (`PlaygroundExportBundleV2`) includes:
- `config` (`PlaygroundConfigV2`)
- `result` (`PlaygroundRunResultV2`)
- `report` (debug snapshot)
- `checksums` (`config_hash`, `result_hash`)

## Verification Steps
1. Import bundle.
2. Replay run using same controls and seed.
3. Compare run facts and summary metrics across runs.
