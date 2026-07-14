---
title: english-coach (plugin)
type: entity
created: 2026-07-13
updated: 2026-07-14
sources: [raw/notes/2026-07-13-english-coach-training-mode-design.md]
tags: [plugin, english-coach]
---

# english-coach (plugin)

A Claude Code plugin that helps a learner improve their English. It began as a **passive**
tool and, per the [[english-coach-training-mode-design]] spec (version bump 1.0.0 →
1.1.0), gains an **active training mode**.

## Passive behavior (baseline)

- A `UserPromptSubmit` hook (`scripts/check.sh`) reviews every prompt.
- Mistakes are logged to `~/.claude/english-mistakes.jsonl` with the shape
  `ts, category, original, corrected, reason, context`. Categories are the fixed set used
  by `check.sh`.
- `/english-coach:stats` (`scripts/stats.sh`) summarizes the logged mistakes.

## Training mode (v1.1.0)

- `/english-coach:train` opens a conversational tutoring session led by [[emma]].
- Emma remembers past sessions via a permanent memory store — see
  [[english-coach-memory-model]].
- The session follows a start / during / end protocol — see
  [[training-mode-session-lifecycle]].
- During a session the passive hook is paused by a sentinel guard so the two do not
  double up.

## Command naming rule

This plugin applies the general [[plugin-command-naming]] rule: the plugin name
`english-coach` already namespaces its commands (`/english-coach:<name>`), so command
**filenames must not repeat the prefix**:

- `commands/english-coach-stats.md` → renamed to `commands/stats.md`
  (still invoked as `/english-coach:stats`; body/behavior unchanged).
- `commands/train.md` → NEW, invoked as `/english-coach:train`.

## File layout (v1.1.0)

- `commands/stats.md` (renamed), `commands/train.md` (new)
- `scripts/check.sh` (sentinel guard added), `scripts/stats.sh` (unchanged),
  `scripts/session-start.sh` (new)
- `hooks/hooks.json` (unchanged)
- `.claude-plugin/plugin.json` (version 1.0.0 → 1.1.0)

## Implementation

Per the [[english-coach-training-mode-plan]], v1.1.0 also adds a `tests/` directory
(`tests/test-session-start.sh`, `tests/test-check-sentinel.sh`) alongside the scripts.
`scripts/session-start.sh` prints three memory sections to stdout (`## Your learner
profile`, `## Recent sessions`, `## Top mistake categories`); the `check.sh` guard is
inserted right after the recursion guard (`export CHECK_ENGLISH_IN_PROGRESS=1`). All
paths are env-overridable via `CHECK_ENGLISH_*` — see [[english-coach-testing]].

## See Also
- [[emma]]
- [[plugin-command-naming]]
- [[training-mode-session-lifecycle]]
- [[english-coach-memory-model]]
- [[english-coach-training-mode-design]]
- [[english-coach-training-mode-plan]]
- [[english-coach-testing]]
