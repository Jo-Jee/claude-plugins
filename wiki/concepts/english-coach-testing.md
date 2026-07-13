---
title: english-coach Testing Approach
type: concept
created: 2026-07-13
updated: 2026-07-13
sources: [raw/notes/2026-07-13-english-coach-training-mode-plan.md]
tags: [english-coach, testing, bash, tdd]
---

# english-coach Testing Approach

How the [[english-coach]] plugin's shell code is tested: plain **bash assertion scripts**
(no framework) that exploit a **test seam** built from `CHECK_ENGLISH_*` environment
overrides. Every path the scripts touch is env-overridable, so a test redirects them all
to a throwaway `mktemp -d` directory and asserts on real filesystem effects and stdout.
This is the concrete testing counterpart of the [[english-coach-training-mode-plan]].

## The test-seam pattern

Each script resolves its paths as `${CHECK_ENGLISH_X:-<default under $HOME>}`. Tests set
those env vars before invoking the script, so nothing touches the real
`~/.claude/english-coach/` store:

- `CHECK_ENGLISH_SENTINEL` — pause sentinel (default
  `~/.claude/english-coach/.session-active`)
- `CHECK_ENGLISH_PROFILE` — `profile.md`
- `CHECK_ENGLISH_SESSIONS` — `sessions.jsonl`
- `CHECK_ENGLISH_MISTAKE_LOG` — `~/.claude/english-mistakes.jsonl`
- `CHECK_ENGLISH_CLAUDE_BIN`, `CHECK_ENGLISH_LOG` — existing seams reused by the
  `check.sh` test

A tiny `assert(desc, result)` helper prints `ok:`/`FAIL:`, sets a `fail` flag, and the
script ends with `ALL PASS` or exits `1`. `trap 'rm -rf "$TMP"' EXIT` cleans up.

## `test-session-start.sh` — what it asserts

- **First run (no memory files):** sentinel is created and holds `^[0-9]+$` (epoch
  seconds); stdout contains all three sections (`## Your learner profile`,
  `## Recent sessions`, `## Top mistake categories`) and a "first session" note.
- **With memory present:** seeds `profile.md`, a `sessions.jsonl` recap line, and two
  `articles` mistake lines, then asserts the profile text, the recent-session summary, and
  a per-category count (`articles … 2`) all appear in stdout.

## `test-check-sentinel.sh` — what it asserts

Stubs `claude` with a script that just `echo OK` (so the non-paused path returns fast),
then drives `check.sh` with a fixed prompt JSON across three cases:

- **Fresh sentinel** (`date +%s`) → no stdout AND sentinel preserved.
- **Stale sentinel** (`now - 8000`, i.e. >7200s) → produces output AND sentinel removed.
- **No sentinel** → normal output.

## Why this style

- No test dependencies beyond `bash`/`jq`; runs anywhere the plugin runs.
- Asserts observable behavior (files written, stdout content, exit silence) rather than
  internals, matching the plugin's script-first design.
- Same convention across old and new scripts, so the training-mode work slots into the
  existing `check.sh`/`stats.sh` test style.

## See Also
- [[english-coach-training-mode-plan]]
- [[english-coach]]
- [[training-mode-session-lifecycle]]
- [[english-coach-memory-model]]
