# sample-ta-1

**Hand-crafted fixture.** Not a real Splunk app — built for Brief's scanner tests.

Modeled on real-world Splunk app structure (RST Threat Feed App was the loose reference for SPL style: `outputlookup` jobs, multi-line searches with backtick comments, mixed-description-quality saved searches).

The layout is designed so every assertion in `tests/test_scanner.py` fires deterministically:

| Asserts | Where it comes from |
|---|---|
| `scan_app()` returns without raising | the whole app structure is valid |
| saved-search count matches `default/savedsearches.conf` | 6 stanzas |
| ≥1 missing-description case | 3 of the 6 lack a usable description (no key, or `description = tmp`) |
| ≥1 safety warning | `\| join` without `\| head`, `index=*`, `\| outputlookup` |
| coverage % in `[0, 100]` | computed from the per-file rollup |

Also exercises:
- `default/` + `local/` layered merge (local overrides one description)
- multi-line continuations (`\` line endings) and backtick comments in SPL
- Simple XML and Studio dashboard variants
- macros, eventtypes, tags, transforms — full surface area of Stage 1
