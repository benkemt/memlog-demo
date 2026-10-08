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

```markdown
---
topic: Expense report export
updated: 2026-10-07T14:22
---

- (capability) CAP-1 export the month as CSV; success: the file opens in Excel with one row per expense
- (decision by user) CAP-1 also exports PDF
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

`specs/first-test/` is a worked example that was produced by running the skill.

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

## Things to observe in the example

Open `specs/first-test/.memlog.md` next to `specs/first-test/spec.md`:

- The input contained two bad entries (`capabilty`, which is a typo, and `toto`, which is not a known
  type). The agent did not fix them in place. It appended `assumption` entries that explain how it
  read them.
- The missing information (why, success criterion, non-goals) shows up as Open Questions in the spec.
  Nothing was invented to fill the gaps.
- The spec was deleted and rebuilt, and the result came out identical, because it is derived only from
  the log. The log itself records each rebuild as `event` entries.

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
