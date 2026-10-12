# Changelog

## v0.1.1 — 2026-10-12
- Documentation layer completed: README (Problem / How it works / Quickstart / why-not-X anchored on the two n8n pipelines and the AI platform / Minimal Fallback / Trade-offs / Limits / FAQ), ALIGNMENT.md 16-item audit, LICENSE (MIT, "zhengming contributors").
- Self-test re-verified green, no code changes needed this round: `python self_test.py` → `SUMMARY: PASS 58/58`.

## v0.1.0 — 2026-10-11
- Initial implementation: action-line detection (bullets/checkboxes, ACTION/TODO/行动项 prefixes), metadata parsing (parenthetical owner/due key-values, @mentions, inline due/by ISO dates) with text cleanup, validation (errors: empty text / missing owner / invalid due; warnings: missing due / past-due vs `--as-of`), summary report with line provenance, CLI (`--json`, `--strict` exit 1, exit 2 on unreadable notes).
- Self-test suite (functional / error / extreme-edge tiers).
