---
name: memlog-spec
description: Create or update a short spec (spec.md) from notes, an idea or the current conversation, keeping every decision in an append-only memlog that the spec is re-derived from on each run. Use when the user says "create a spec", "update the spec", "add this to the spec" or "rebuild the spec".
---

# Memlog spec

## The principle

`.memlog.md` is the source of truth: one line per decision, in the order it happened, never edited.
`spec.md` is **derived** from it: rewritten in full on every run, never edited by hand. A hand edit
to `spec.md` is lost on the next run; a change goes in as a new memlog entry instead.

Every write goes through the script, run with `py` (`<skill>` is this skill's folder):

```
py <skill>/scripts/memlog.py init   --workspace specs/<slug> --field topic="<what is specced>"
py <skill>/scripts/memlog.py append --workspace specs/<slug> --type <type> --text "<one line>"
```

Each command prints `{"ok": true, "memlog": "...", "entries": N}`. Do not read the file back to check it.

## Workspace

`specs/<slug>/` under the working directory, holding `.memlog.md` and `spec.md`. The slug names the
thing being specced. Same slug, same folder: a second run updates the spec in place.

## Entry types

| `--type` | Holds | Goes to |
|---|---|---|
| `why` | the need behind the work | Why |
| `capability` | `CAP-N <intent>; success: <test>` | Capabilities |
| `constraint` | a rule that excludes options | Constraints |
| `non-goal` | something explicitly out of scope | Non-goals |
| `assumption` | a call made without the user's confirmation | Assumptions |
| `question` | an open point | Open Questions, until a later entry answers it |
| `decision` | a choice that changes any of the above | the section its content changes |
| `note`, `event` | context and process (start, validation, re-derivation) | stays in the memlog |

## Steps

1. **Load.** If `specs/<slug>/.memlog.md` exists, read it in full: this is the only time it is read.
   Otherwise run `init`.
2. **Log.** For each point in the input, `append` one entry as it is settled. A new capability takes
   the next unused `CAP-N`; an ID is never reused or renumbered, even after the capability is dropped.
   To change or drop a point, append a new entry that names the ID or the point it replaces. Never
   edit or delete a line. When two entries still in force disagree, ask the user; the answer is a new
   `decision` entry.
3. **Derive.** Read `assets/spec-template.md` and write `spec.md` in full from the memlog, using the
   table above. The latest entry on a point wins; superseded entries do not appear. Write only what
   the memlog says: a gap becomes an Open Question, not an invented answer.
4. **Validate.** Check two things, fix `spec.md` if needed, then log each verdict as an `event`:
   - coherence: every capability has an intent and a success, there is at least one non-goal;
   - preservation: every entry still in force appears in `spec.md`.
   Then `append --type event --text "spec re-derived: <what changed>"`.
5. **Report.** Give the spec path, the number of capabilities and the open questions, one line each.
