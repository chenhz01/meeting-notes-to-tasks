#!/usr/bin/env python3
"""meeting-notes-to-tasks: extract action items from meeting notes into a
validated task schema {text, owner, due} with a completeness report.
Deliberately regex-and-rules, not AI: deterministic and offline.
Pure standard library."""

import argparse
import json
import re
import sys
from datetime import date

ACTION_PREFIX_RE = re.compile(r"^\s*(?:[-*+]\s*\[[ xX]\]\s*|[-*+]\s+|(?:ACTION|TODO|行动项)\s*[:：]\s*)", re.IGNORECASE)
META_PAREN_RE = re.compile(r"\(([^()]*)\)\s*$")
KV_RE = re.compile(r"\b(owner|due|owner_by)\s*[:=]\s*([^,;]+)", re.IGNORECASE)
AT_OWNER_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9._-]+)")
DUE_INLINE_RE = re.compile(r"\b(?:due|by)\s*[:=]?\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _valid_date(s):
    try:
        y, m, d = (int(x) for x in s.split("-"))
        date(y, m, d)
        return s
    except Exception:
        return None


def extract_tasks(text):
    """Parse notes text; return raw task dicts with source line numbers."""
    tasks = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not ACTION_PREFIX_RE.match(line):
            continue
        body = ACTION_PREFIX_RE.sub("", line, count=1).strip()
        if not body:
            continue
        owner, due, meta_removed = None, None, body
        pm = META_PAREN_RE.search(body)
        if pm:
            inner = pm.group(1)
            kv = dict((m.group(1).lower(), m.group(2).strip()) for m in KV_RE.finditer(inner))
            if "owner" in kv:
                owner = kv["owner"].lstrip("@").strip() or None
            if "due" in kv:
                dm = DATE_RE.search(kv["due"])
                if dm:
                    due = dm.group(0)
            if owner is not None or due is not None:
                meta_removed = body[:pm.start()].strip()
        if owner is None:
            om = AT_OWNER_RE.search(meta_removed)
            if om:
                owner = om.group(1)
                meta_removed = (meta_removed[:om.start()] + meta_removed[om.end():]).strip(" -,")
        if due is None:
            dm = DUE_INLINE_RE.search(meta_removed)
            if dm:
                due = dm.group(1)
                meta_removed = (meta_removed[:dm.start()] + meta_removed[dm.end():]).strip(" -,")
        tasks.append({"text": meta_removed.strip(), "owner": owner, "due": due, "line": lineno})
    return tasks


def validate_task(task, as_of=None):
    """Return (errors, warnings) lists of strings for one task."""
    errors, warnings = [], []
    if not task["text"]:
        errors.append("empty_text")
    if not task["owner"]:
        errors.append("missing_owner")
    if not task["due"]:
        warnings.append("missing_due")
    elif not _valid_date(task["due"]):
        errors.append("invalid_due")
    elif as_of:
        try:
            a = date(*(int(x) for x in as_of.split("-")))
            d = date(*(int(x) for x in task["due"].split("-")))
            if d < a:
                warnings.append("already_past")
        except ValueError:
            errors.append("invalid_due")
    return errors, warnings


def process(text, as_of=None):
    tasks = extract_tasks(text)
    report_tasks = []
    n_err = n_warn = n_valid = 0
    for t in tasks:
        errs, warns = validate_task(t, as_of)
        n_err += len(errs)
        n_warn += len(warns)
        if not errs:
            n_valid += 1
        report_tasks.append({"task": t, "errors": errs, "warnings": warns})
    return {
        "tasks": report_tasks,
        "summary": {
            "total": len(tasks),
            "valid": n_valid,
            "error_count": n_err,
            "warning_count": n_warn,
        },
    }


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="meeting-notes-to-tasks",
        description="Extract action items from meeting notes into a validated {text, owner, due} task schema.",
    )
    p.add_argument("notes", help="meeting notes file (markdown or plain text)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--strict", action="store_true", help="exit 1 if any task missing owner/due or invalid")
    p.add_argument("--as-of", default=date.today().isoformat(), help="reference date for past-due warnings")
    args = p.parse_args(argv)

    try:
        with open(args.notes, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        print("error: cannot read notes: %s" % exc, file=sys.stderr)
        return 2

    result = process(text, args.as_of)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        s = result["summary"]
        print("tasks=%d valid=%d errors=%d warnings=%d" %
              (s["total"], s["valid"], s["error_count"], s["warning_count"]))
        for t in result["tasks"]:
            flags = ",".join(t["errors"] + t["warnings"]) or "ok"
            print("  L%-4d [%s] %s" % (t["task"]["line"], flags, t["task"]["text"][:60]))
    if args.strict:
        bad = any(t["errors"] or "missing_owner" in t["warnings"] or "missing_due" in t["warnings"]
                  for t in result["tasks"])
        if bad:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
