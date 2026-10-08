# memlog-demo

An educational repository that shows how a **memlog** works: the append-only memory file used in the
[BMad Method](https://github.com/bmad-code-org/BMAD-METHOD). The demo is a small Claude Code skill,
`memlog-spec`, that keeps every decision about a feature in a memlog and rebuilds a short spec from it
on every run.

The code is deliberately minimal. Its job is to make the pattern easy to read, not to be a production
tool.

## The idea in one paragraph

An AI agent working across several sessions forgets things. It also tends to "improve" a document
every time it rewrites it, so earlier decisions get lost quietly. A memlog fixes this by splitting
the work in two:

- **`.memlog.md` is the source of truth.** It holds one line per decision, in the order the
  decisions happened. Lines are only ever appended. Nothing is edited or deleted.
- **`spec.md` is derived.** It is rewritten in full from the memlog on every run and never edited by
  hand. To change the spec, you append a new memlog entry and re-derive.

So the history is never lost, and the spec always reflects the latest decision on each point.

## The three memlog rules

These come from `memlog.py` (a short version of BMad's script):

1. **Append-only and chronological.** There is no edit or delete command. A later entry supersedes
   an earlier one.
2. **Blind writes.** Every command prints the new state as one line of JSON
   (`{"ok": true, "memlog": "...", "entries": N}`). The agent never re-reads the file during a
   session. It reads the memlog only once, when it resumes work.
3. **No status field.** Progress such as "done" or "blocked" is recorded as an entry too
   (`--type event`).

## What a memlog looks like

An excerpt from the example in this repository:

```markdown
---
topic: Expense report export
updated: 2026-10-08T09:32
---

- (capability) CAP-2 the system emails the previous month's CSV to the accounting mailbox on the 1st of each month; success: on the 1st, the accounting mailbox receives the CSV of the previous month
- (question) which CSV layout (columns, separator, date format) does the accounting software import?
- (decision by user) CAP-2 dropped: accounting prefers to download the file themselves, no automatic email
```

The frontmatter holds metadata. Each entry is a single line written as `- (type) text` or
`- (type by who) text`.

## Repository layout

```
.claude/skills/memlog-spec/
  SKILL.md                 the skill: steps the agent follows (load, log, derive, validate, report)
  scripts/memlog.py        the memlog tool: init, append, set
  assets/spec-template.md  the shape of the derived spec.md
specs/<slug>/
  .memlog.md               the append-only log for one spec
  spec.md                  the spec derived from it
```

`specs/expense-report-export/` is a worked example produced by running the skill. It is described
in [The worked example](#the-worked-example).

## How the skill uses the memlog

Each run of `memlog-spec` goes through five steps:

1. **Load.** Read `specs/<slug>/.memlog.md` in full if it exists; this is the only time it is read.
   Otherwise create it with `init`.
2. **Log.** Append one entry for each point that has been settled. Capabilities get stable IDs
   (`CAP-1`, `CAP-2`, ...) that are never reused. To change or drop a point, append a new entry that
   names it.
3. **Derive.** Rewrite `spec.md` from the memlog, following the template. The latest entry on a point
   wins. Any gap becomes an Open Question instead of an invented answer.
4. **Validate.** Check coherence (every capability has an intent and a success criterion, and there
   is at least one non-goal) and preservation (every entry still in force appears in the spec). Log
   both verdicts as `event` entries.
5. **Report.** Give the spec path, the number of capabilities and the open questions.

Entry types and where each one lands in the spec:

| Type | Holds | Spec section |
|---|---|---|
| `why` | the need behind the work | Why |
| `capability` | `CAP-N <intent>; success: <test>` | Capabilities |
| `constraint` | a rule that excludes options | Constraints |
| `non-goal` | something explicitly out of scope | Non-goals |
| `assumption` | a call made without the user's confirmation | Assumptions |
| `question` | an open point | Open Questions, until answered |
| `decision` | a choice that changes any of the above | the section it changes |
| `note`, `event` | context and process | stays in the memlog only |

## The worked example

`specs/expense-report-export/` follows a fictional team that specs a month-end export for its
expense app. At month end, accounting retypes every approved expense into the accounting software by
hand. The skill was run three times, and each run is marked in the memlog by an `event` entry
(`run 1 started`, `run 2 started`, `run 3 started`). Open `.memlog.md` next to `spec.md` and follow
the runs:

**Run 1, create.** The product owner's notes become 10 entries:

- one `why`;
- two capabilities: CAP-1, a CSV export, and CAP-2, an automatic email to accounting on the 1st;
- two constraints: only approved expenses are exported, and only the finance role can export;
- one non-goal: no integration with the accounting software's API;
- one assumption: amounts stay in their approval currency;
- one question: which CSV layout does the accounting software import?

The first `spec.md` is derived from those entries.

**Run 2, update.** Accounting's answers are appended. Nothing above them is edited:

- A `decision` answers the CSV layout question. The question leaves Open Questions, and the layout
  appears under Constraints.
- A `decision` drops CAP-2. It disappears from the spec, but its line stays in the memlog, so the
  history shows that an automatic email was considered and why it was dropped.
- A new capability takes **CAP-3**, not CAP-2. IDs are never reused, so "CAP-2" always means the
  email, wherever it is quoted.
- A new `question` about the PDF totals becomes the spec's only open question.

**Run 3, rebuild.** `spec.md` was deleted and derived again from the memlog alone. The result is
identical to the run 2 spec, which shows that the spec holds nothing the log does not.

Other things to notice:

- **Assumptions stay visible.** The currency assumption was never confirmed, so it stays under
  Assumptions. It would move only if a later `decision` confirmed or replaced it.
- **Validation is logged.** After each derivation, the coherence and preservation checks are recorded
  as `event` entries, followed by a `spec re-derived: ...` line that summarises what changed.
- **History is not in the spec.** `spec.md` shows only the current state. To know why the spec looks
  the way it does, read the memlog.

## Try it

**With Claude Code**, from the repository root:

```
/memlog-spec create a spec for <your idea>
/memlog-spec add this to the spec: <a new decision>
/memlog-spec rebuild the spec
```

**With the script alone** (Python 3; `py` is the Windows launcher, use `python3` elsewhere):

```
py .claude/skills/memlog-spec/scripts/memlog.py init   --workspace specs/demo --field topic="My feature"
py .claude/skills/memlog-spec/scripts/memlog.py append --workspace specs/demo --type capability --text "CAP-1 ...; success: ..."
py .claude/skills/memlog-spec/scripts/memlog.py set    --workspace specs/demo --key topic --value "My renamed feature"
```

## Simplifications compared to BMad

- `append` uses a plain file append. That is enough for one writer. BMad's version opens a
  `FILE_APPEND_DATA` handle on Windows, so parallel subagents appending at the same moment never
  overwrite each other.
- `init` and `set` rewrite the file atomically (temp file, fsync, rename), so a crash leaves either
  the old file or the new one, never half of one.
