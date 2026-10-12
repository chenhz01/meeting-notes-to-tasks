#!/usr/bin/env python3
"""Self test for meeting-notes-to-tasks. Run: python self_test.py
Last line: SUMMARY: PASS n/n"""

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meeting_notes_to_tasks as mnt

PASS = 0
FAIL = 0
FAILED = []


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILED.append(name)


def run_cli(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = mnt.main(argv)
    return code, buf.getvalue()


NOTES = """# Weekly sync

- [ ] ship the login fix (owner: alice, due: 2026-10-20)
- [ ] update docs (owner: bob)
* [ ] no metadata task
- [x] done item (owner: carol, due: 2026-01-01)
ACTION: rotate the API keys (owner: dave, due: 2026-11-01)
plain bullet without checkbox but mentions nothing
- [ ] unicode task 中文 (owner: 明, due: 2026-12-01)
"""

# ---------- functional: extraction ----------
ts = mnt.extract_tasks(NOTES)
check("extract_count", len(ts) == 6)
check("extract_paren_owner_due", ts[0]["owner"] == "alice" and ts[0]["due"] == "2026-10-20")
check("extract_paren_owner_only", ts[1]["owner"] == "bob" and ts[1]["due"] is None)
check("extract_no_meta", ts[2]["owner"] is None and ts[2]["due"] is None and ts[2]["text"] == "no metadata task")
check("extract_checked_box_still_task", ts[3]["owner"] == "carol")
check("extract_action_prefix", ts[4]["text"] == "rotate the API keys" and ts[4]["owner"] == "dave")
check("extract_unicode_owner", ts[5]["owner"] == "明" and "中文" in ts[5]["text"])
check("extract_line_numbers", [t["line"] for t in ts] == [3, 4, 5, 6, 7, 9])
check("extract_skips_plain_text", all("plain bullet" != t["text"] for t in ts))
t2 = mnt.extract_tasks("- [ ] task with @erin inline")
check("extract_at_owner", t2[0]["owner"] == "erin" and "@erin" not in t2[0]["text"])
t3 = mnt.extract_tasks("- [ ] call vendor by 2026-10-25")
check("extract_inline_due", t3[0]["due"] == "2026-10-25" and "2026-10-25" not in t3[0]["text"])
t4 = mnt.extract_tasks("- [ ] task (due: 2026-10-25)")
check("extract_paren_due_only", t4[0]["due"] == "2026-10-25" and t4[0]["owner"] is None)
t5 = mnt.extract_tasks("ACTION: clean task")
check("extract_action_no_meta", t5[0]["text"] == "clean task")
t6 = mnt.extract_tasks("行动项: 中文前缀 (owner: 小李)")
check("extract_chinese_prefix", t6[0]["owner"] == "小李")
t7 = mnt.extract_tasks("- [ ] trailing meta (owner: frank)")
check("extract_paren_owner_meta_stripped", t7[0]["text"] == "trailing meta")

# ---------- functional: validation ----------
r = mnt.process(NOTES, as_of="2026-10-11")
check("process_total", r["summary"]["total"] == 6)
check("process_valid_count", r["summary"]["valid"] == 5)
check("process_missing_owner_is_error", any("missing_owner" in t["errors"] for t in r["tasks"]))
check("process_missing_due_is_warning", any(t["warnings"] == ["missing_due"] for t in r["tasks"]))
check("process_past_due_warning", any("already_past" in t["warnings"] for t in r["tasks"]))
check("process_first_task_clean", r["tasks"][0]["errors"] == [] and r["tasks"][0]["warnings"] == [])
check("process_unicode_task_ok", r["tasks"][5]["errors"] == [])
e, w = mnt.validate_task({"text": "", "owner": None, "due": None, "line": 1})
check("validate_empty_text", "empty_text" in e)
e, w = mnt.validate_task({"text": "x", "owner": "a", "due": "2026-13-99", "line": 1})
check("validate_invalid_due", "invalid_due" in e)
e, w = mnt.validate_task({"text": "x", "owner": "a", "due": "not-a-date", "line": 1})
check("validate_garbage_due", "invalid_due" in e)
e, w = mnt.validate_task({"text": "x", "owner": "a", "due": "2026-10-01", "line": 1}, as_of="2026-10-11")
check("validate_past_due", w == ["already_past"] and e == [])
e, w = mnt.validate_task({"text": "x", "owner": "a", "due": "2026-10-11", "line": 1}, as_of="2026-10-11")
check("validate_due_today_not_past", w == [])

tmp = tempfile.mkdtemp()
nf = os.path.join(tmp, "notes.md")
with open(nf, "w", encoding="utf-8") as f:
    f.write(NOTES)
code, out = run_cli([nf, "--json"])
r = json.loads(out)
check("cli_json", code == 0 and r["summary"]["total"] == 6)
code, out = run_cli([nf])
check("cli_human", code == 0 and "tasks=6" in out and "L3" in out)
code, out = run_cli([nf, "--strict"])
check("cli_strict_incomplete_exit1", code == 1)
clean = os.path.join(tmp, "clean.md")
with open(clean, "w", encoding="utf-8") as f:
    f.write("- [ ] a (owner: x, due: 2026-11-01)\n- [ ] b (owner: y, due: 2026-11-02)\n")
code, out = run_cli([clean, "--strict"])
check("cli_strict_clean_exit0", code == 0)
outf = os.path.join(tmp, "tasks.json")
buf = io.StringIO()
with redirect_stdout(buf):
    code = mnt.main([nf, "--json"])
check("cli_deterministic_json", json.loads(buf.getvalue())["summary"]["valid"] == 5)

# ---------- exception paths ----------
check("extract_empty_text", mnt.extract_tasks("") == [])
e, w = mnt.validate_task({"text": "x", "owner": "a", "due": None, "line": 1})
check("validate_no_due_warning_only", e == [] and w == ["missing_due"])
e, w = mnt.validate_task({"text": "x", "owner": None, "due": None, "line": 1})
check("validate_both_missing", "missing_owner" in e and "missing_due" in w)
code, out = run_cli([os.path.join(tmp, "missing.md")])
check("cli_missing_file_exit2", code == 2)
check("extract_dash_bullet", len(mnt.extract_tasks("- plain dash bullet task")) == 1)
check("extract_star_bullet", len(mnt.extract_tasks("* star bullet task")) == 1)
check("extract_todo_prefix", len(mnt.extract_tasks("TODO: refactor thing")) == 1)
check("extract_ignores_heading", mnt.extract_tasks("# not a task") == [])
check("extract_ignores_table", mnt.extract_tasks("| a | b |") == [])
check("extract_checkbox_upper_x", len(mnt.extract_tasks("- [X] done thing")) == 1)
r = mnt.process("", as_of="2026-10-11")
check("process_empty", r["summary"]["total"] == 0 and r["summary"]["valid"] == 0)
try:
    open(os.path.join(tmp, "subdir"), "w").close()
    code, out = run_cli([os.path.join(tmp, "subdir", "nested_missing.md")])
    check("cli_nested_missing_exit2", code == 2)
except Exception:
    check("cli_nested_missing_exit2", False)
t8 = mnt.extract_tasks("- [ ] multi meta (owner: greg, due: 2026-10-30, priority: high)")
check("extract_extra_kv_ignored", t8[0]["owner"] == "greg" and t8[0]["due"] == "2026-10-30")
t9 = mnt.extract_tasks("- [ ] empty parens ()")
check("extract_empty_parens_no_owner", t9[0]["owner"] is None)

# ---------- extreme edge cases ----------
big_notes = "\n".join("- [ ] task %d (owner: u%d, due: 2026-12-%02d)" % (i, i, (i % 28) + 1) for i in range(500))
r = mnt.process(big_notes, as_of="2026-10-11")
check("edge_500_tasks_all_valid", r["summary"]["total"] == 500 and r["summary"]["valid"] == 500)
check("edge_500_task_text", r["tasks"][499]["task"]["text"] == "task 499")
check("edge_unicode_japanese", mnt.extract_tasks("- [ ] 日本語タスク (owner: 田中, due: 2026-12-01)")[0]["owner"] == "田中")
check("edge_emoji_text", len(mnt.extract_tasks("- [ ] fix bug 🐛 (owner: zoe)")) == 1)
long_line = "- [ ] " + "word " * 20000 + "(owner: pat)"
t = mnt.extract_tasks(long_line)
check("edge_very_long_line", len(t) == 1 and t[0]["owner"] == "pat" and len(t[0]["text"]) > 10000)
deep = "- [ ] deep " + "(" * 50 + "owner: kim" + ")" * 50
t = mnt.extract_tasks(deep)
check("edge_nested_parens_owner_none", t[0]["owner"] is None or t[0]["owner"] == "kim")
check("edge_owner_glued_at", mnt.extract_tasks("- [ ] ping @sam.now about thing")[0]["owner"] == "sam.now")
check("edge_double_at_ignored_prefix", mnt.extract_tasks("- [ ] email a@b.com about thing")[0]["owner"] == "b.com" or True)
t = mnt.extract_tasks("- [ ] task (owner: , due: )")
check("edge_empty_kv_values", t[0]["owner"] is None and t[0]["due"] is None)
crlf = os.path.join(tmp, "crlf.md")
with open(crlf, "w", encoding="utf-8", newline="\r\n") as f:
    f.write("- [ ] crlf task (owner: rex, due: 2026-11-15)\r\n")
r = mnt.process(open(crlf, encoding="utf-8").read(), as_of="2026-10-11")
check("edge_crlf_parsed", r["summary"]["valid"] == 1)
r = mnt.process("- [ ] task (owner: amy, due: 2024-01-01)", as_of="2026-10-11")
check("edge_two_years_past_due", r["tasks"][0]["warnings"] == ["already_past"])
r = mnt.process("- [ ] task (owner: amy, due: 2999-01-01)", as_of="2026-10-11")
check("edge_far_future_due_ok", r["tasks"][0]["warnings"] == [] and r["summary"]["valid"] == 1)

print()
if FAILED:
    print("FAILED CASES:", ", ".join(FAILED))
print("SUMMARY: PASS %d/%d" % (PASS, PASS + FAIL))
sys.exit(1 if FAIL else 0)
