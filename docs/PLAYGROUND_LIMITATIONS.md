# Playground Limitations and Browser Support

## Supported Browsers
- Latest Chrome, Edge, Firefox, and Safari (evergreen releases).

## Runtime Limits
- Max steps: 500
- Max episodes: 20
- Max scenarios: 64
- Max run time: 45 seconds
- Max import bytes: 1,000,000

## Known Constraints
- Runtime depends on Pyodide CDN availability.
- Very large scenario products may hit memory/runtime limits.
- Web worker cancellation is cooperative and restarts runtime state.
- Legacy payloads with unknown schema versions are rejected.
