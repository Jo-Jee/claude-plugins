---
title: english-coach Training Mode — Implementation Plan
type: source
created: 2026-07-13
updated: 2026-07-13
sources: [raw/notes/2026-07-13-english-coach-training-mode-plan.md]
tags: [english-coach, plan, training-mode, tdd]
---

# english-coach Training Mode — Implementation Plan

The task-by-task implementation plan (2026-07-13) that realizes the
[[english-coach-training-mode-design]] spec. Where the design fixes the *what and why*,
this plan pins the concrete *how*: exact file paths, script bodies, bash test suites, and
a per-task TDD + commit workflow. It targets the [[english-coach]] plugin, version
1.0.0 → 1.1.0.

Meant to be executed with `superpowers:subagent-driven-development` (or
`superpowers:executing-plans`); each step uses `- [ ]` checkboxes for tracking.

## Global constraints (implementation-level)

- Command filenames must NOT repeat the `english-coach` namespace prefix → files are
  `stats.md`, `train.md`. See [[english-coach]].
- Mistake-log entries use the exact existing JSONL shape
  (`{ts, category, original, corrected, reason, context}`) with `category` from the fixed
  set (`articles, agreement, tense, prepositions, capitalization, plurals, spelling,
  word-choice, word-order, contractions, punctuation, structure, other`, plus `rewrite`
  as used by `check.sh`). See [[english-coach-memory-model]].
- All new paths are overridable via `CHECK_ENGLISH_*` env vars (test seam). See
  [[english-coach-testing]].
- Sentinel staleness window is exactly `7200`s (2h); governs the sentinel ONLY, never
  memory. See [[training-mode-session-lifecycle]].

## File structure

```
english-coach/
  commands/
    stats.md          # renamed from english-coach-stats.md (body unchanged)
    train.md          # NEW — persona + session protocol
  scripts/
    check.sh          # MODIFY — add sentinel guard near top
    stats.sh          # unchanged
    session-start.sh  # NEW — write sentinel + print memory context
  tests/
    test-session-start.sh   # NEW
    test-check-sentinel.sh  # NEW
  .claude-plugin/plugin.json  # MODIFY — 1.0.0 -> 1.1.0
README.md                     # MODIFY — document training mode
```

## Task breakdown (5 tasks)

1. **`session-start.sh`** (new) + `test-session-start.sh` — writes epoch seconds to the
   sentinel and prints a markdown memory block (`## Your learner profile`,
   `## Recent sessions`, `## Top mistake categories`) to stdout via `jq`/`awk`. This is
   the start half of [[training-mode-session-lifecycle]].
2. **`check.sh` sentinel guard** (modify) + `test-check-sentinel.sh` — inserts the guard
   right after the recursion-guard block (`export CHECK_ENGLISH_IN_PROGRESS=1`): fresh
   sentinel (<7200s) → `exit 0` silent; stale → `rm -f` and resume; also validates the
   sentinel holds a plain epoch integer.
3. **Rename `english-coach-stats.md` → `stats.md`** via `git mv` (body unchanged) so
   invocation becomes `/english-coach:stats`.
4. **`train.md`** (new) — the `/english-coach:train` slash command carrying the [[emma]]
   persona, the `!`-preamble that runs `session-start.sh`, and the ordered end-of-session
   save protocol (recap → profile → mistakes → remove sentinel → goodbye).
5. **Version bump + README** — `plugin.json` 1.0.0 → 1.1.0; document training mode and
   the new memory files/paths.

## TDD / commit workflow

Each code task follows the same loop: write the failing bash test → run it and confirm
the expected failure → write the implementation → run the test to `ALL PASS` → `chmod +x`
and a scoped Conventional-Commit (`feat(english-coach): …`, `refactor(…)`, `docs(…)`).
The plan is verified against the spec by a closing **Self-Review** (spec-coverage
checklist, placeholder scan, and env-var/name/window consistency check).

## Test approach

Two bash assertion scripts drive the code tasks, using `CHECK_ENGLISH_*` env overrides
against `mktemp -d` dirs and a stubbed `claude` binary. Detailed in
[[english-coach-testing]].

## See Also
- [[english-coach-training-mode-design]] — the spec this plan implements
- [[english-coach-testing]]
- [[english-coach]]
- [[emma]]
- [[training-mode-session-lifecycle]]
- [[english-coach-memory-model]]
