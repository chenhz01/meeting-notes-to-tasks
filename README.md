# meeting-notes-to-tasks

meeting-notes-to-tasks extracts action items from meeting notes into a validated `{text, owner, due}` task schema, with a completeness report (errors, warnings, per-line provenance). Deliberately regex-and-rules, not AI: deterministic, offline, and free. Use it to turn bullet lists and TODO lines into a checkable task list instead of letting action items evaporate after the call. Confidence: High (≥80%) for the documented extraction patterns, per the 58-check suite.

## Problem

Meeting notes record action items as bullets, "TODO:" lines, and asides with owners and dates scattered in parentheses. Nobody converts them while context is fresh; a week later the notes are archaeology. LLM-based extractors solve this at the cost of API keys, non-determinism, and hallucinated owners. What is missing is a strict offline extractor that *refuses to invent* — it only reports what the text literally contains, then flags what is incomplete.

## How it works

1. **Detect action lines** — bullets (`-`, `*`, `+`, with optional `[x]` checkbox), and `ACTION:` / `TODO:` / `行动项：` prefixed lines.
2. **Parse metadata** —
   - trailing parenthetical `(owner: X, due: 2026-10-20)`, with `owner=`/`owner_by=`/`due:`/`due=` key-value variants;
   - `@name` mentions anywhere in the line (owner);
   - inline `due 2026-10-20` / `by 2026-10-20` (due date), ISO dates only.
   Metadata found in the parenthetical is removed from the task text; `@owner` and inline dates are stripped from the text too, so `{text}` stays clean.
3. **Validate** — errors: empty text, missing owner, invalid due date; warnings: missing due, due date already past (against `--as-of`).
4. **Report** — per-task `{task, errors, warnings}` plus a summary `{total, valid, error_count, warning_count}`; `--strict` exits 1 when anything is incomplete.

## Quickstart (~2 min)

```bash
# step 1: extract from notes (~1 s)
python meeting_notes_to_tasks.py notes.md
# step 2: JSON report + strict CI gate
python meeting_notes_to_tasks.py notes.md --json --strict
# step 3: review with a fixed reference date for past-due warnings
python meeting_notes_to_tasks.py notes.md --as-of 2026-10-12
# full suite (~3 s)
python self_test.py   # SUMMARY: PASS 58/58 [Measured]
```

Library use: `extract_tasks(text)` → raw tasks; `process(text, as_of)` → full report.

## Why not X? (as of 2026-10-12)

- **MinaSaad1/n8n-meeting-notes-to-tasks** (2★) — "Webhook-triggered n8n workflow that turns meeting transcripts into Notion tasks with owners, decisions log…". Strong at *delivery* (webhook → Notion), but requires an n8n instance and a transcription pipeline; this repo is a single stdlib file you can run on any text file, with no infra.
- **shaikhaalbaho/meeting-notes-to-tasks-ai** — "AI-enhanced platform that extracts action items from meeting notes into structured tasks (JSON-validated)". LLM extraction gives recall on messy prose but is non-deterministic and can invent owners/dates; this repo never invents — unmatched metadata becomes a visible `missing_owner`/`missing_due` warning instead of a guess.
- **ortholeshkin-oss/n8n-meeting-notes-to-tasks** — "Turn meeting transcripts into structured action items with owners and due dates, plus decisions, risks, open q…". Same n8n delivery pattern with broader output types (decisions/risks); this repo narrows scope to validated action items and adds line-number provenance for review.

## Minimal Fallback (PLAN B)

No Python: `grep -nE '^\s*[-*+] \[ \]|TODO|ACTION' notes.md` lists candidate action lines with line numbers; eyeball owners and dates from there. You lose metadata parsing, validation, past-due warnings, and the strict exit code — but you keep the extraction starting point.

## Design Trade-offs

Priority order: **no-invention > determinism > zero-dependency > recall**. Regex extraction deliberately misses paraphrased action items buried in prose paragraphs rather than risk hallucinating owners or deadlines; every extracted field is traceable to its source line. ISO dates only (`YYYY-MM-DD`) — "next Friday" and "10/20" are rejected, because locale-relative dates are exactly where silent wrongness enters. Missing `due` is a *warning*, not an error: an ownerless task is useless, but a dateless task is often legitimate ("ASAP", ongoing).

## Limits & Second-order Effects

- Prose-formatted action items ("Sarah will draft the spec by Friday") are invisible — no NLP, by design.
- Owner names come from `@mentions` or `owner:` fields; real names without markers are not detected.
- Multiple `@mentions` in one line take the first match; multiline tasks (bullets spanning lines) are not merged.
- Second-order: teams that trust the summary count may treat "valid=8" as "all action items captured" — the tool cannot know what it failed to *detect*, only that what it found is well-formed. Keep a human pass on the raw notes.
- `--strict` in CI can pressure note-takers into always writing `owner:`/`due:` even when unknown, degrading note honesty.

## FAQ

**Why no AI extraction?** Because the failure mode of an invented owner ("assign to alice" when nobody said alice) is worse than a visible gap; this tool's contract is that everything it reports exists verbatim in the notes.

**Can I use it on transcripts?** Yes, if speakers prefix action lines with TODO/ACTION or bullets; free-flowing transcript prose will under-detect.

### When NOT to use this tool?

- Your notes are unstructured prose — an LLM extractor with human review fits better.
- You need calendar integration or assignment sync — this outputs a validated list, not integrations.
- Deadline language is relative ("next week") — ISO-only parsing will flag everything.
- You want decisions/risks/open-questions extraction too — out of scope; use a broader transcript pipeline.

## License

MIT — see `LICENSE`. Contact: hcac4735@agent.qq.com

---

[Core Assumptions]
- Action items in meeting notes appear as bullets or TODO/ACTION-prefixed lines far more often than as buried prose.
- An extractor that never invents fields is more useful than a smarter one that sometimes fabricates owners or dates.
- ISO dates are the only deadlines safe to parse without locale context.
- Missing due dates are acceptable warnings; missing owners are hard errors, as of 2026-10-12.

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 55 purpose-built AI-engineering tools across neglected niches.

Related tools: [email-triage-spec](https://github.com/chenhz01/email-triage-spec) · [focus-data-aggregator](https://github.com/chenhz01/focus-data-aggregator) · [git-history-hygiene](https://github.com/chenhz01/git-history-hygiene)
