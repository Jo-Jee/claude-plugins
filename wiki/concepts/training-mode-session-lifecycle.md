---
title: Training Mode Session Lifecycle
type: concept
created: 2026-07-13
updated: 2026-07-13
sources: [raw/notes/2026-07-13-english-coach-training-mode-design.md]
tags: [english-coach, session, lifecycle]
---

# Training Mode Session Lifecycle

The start / during / end protocol for an [[english-coach]] training session led by
[[emma]]. Central to it is a **pause sentinel** that mutes the passive review hook while a
session is live.

## 1. Start (`/english-coach:train`)

The command markdown runs `scripts/session-start.sh` in its `!`-prefixed preamble. The
script:

1. Creates the pause sentinel `~/.claude/english-coach/.session-active` containing the
   current epoch seconds.
2. Prints the learner's memory into the command context:
   - full `profile.md` (if present),
   - the last ~3 lines of `sessions.jsonl`,
   - a top-categories summary from `english-mistakes.jsonl` (reusing the logic style of
     `stats.sh`).

The command body then instructs Emma to open with a natural, personalized greeting that
references the last session, and to ease into conversation while steering toward weak
spots.

## 2. During

- Natural conversation; gentle inline corrections only.
- Emma keeps a running mental note of notable mistakes to persist at the end.
- The passive hook stays paused (see sentinel guard below).

## 3. End (save protocol)

Triggered when the learner signals a stop (e.g. "bye", "let's stop") or Emma wraps up.
Emma performs the save protocol using Write/Edit + Bash/append, as an explicit ordered
checklist:

1. Append a recap object to `~/.claude/english-coach/sessions.jsonl`.
2. Update `~/.claude/english-coach/profile.md` with new durable facts and an updated
   impression.
3. Append notable corrections to `~/.claude/english-mistakes.jsonl` using the **exact**
   existing JSONL shape (`ts, category, original, corrected, reason, context`), with
   `category` from the existing `check.sh` category set, so `stats.sh` reads them
   uniformly.
4. Remove the sentinel `~/.claude/english-coach/.session-active`.
5. Say a warm goodbye.

See [[english-coach-memory-model]] for the file details.

## Sentinel guard in `check.sh`

A guard is added near the top (after the recursion guard, before the LLM call):

```bash
SENTINEL="$HOME/.claude/english-coach/.session-active"
if [ -f "$SENTINEL" ]; then
  started=$(cat "$SENTINEL" 2>/dev/null)
  now=$(date +%s)
  # Fresh sentinel (< 2h) → a training session is live; stay silent.
  if [ -n "$started" ] && [ $((now - started)) -lt 7200 ]; then
    exit 0
  fi
  # Stale sentinel → forgotten goodbye; remove it and resume normal review.
  rm -f "$SENTINEL"
fi
```

- The **2h window governs only the sentinel, never memory**.
- Slash commands already `exit 0` earlier in `check.sh`, so `/english-coach:train` itself
  is never reviewed; the guard covers the normal prompts typed *during* the session.
- Path is overridable for tests via an env var consistent with the existing
  `CHECK_ENGLISH_*` convention (e.g. `CHECK_ENGLISH_SENTINEL`).

## Risks addressed

- Forgotten goodbye → 2h staleness guard auto-resumes the hook.
- Model skips the save → ordered checklist in the command body; stale sentinel self-heals.

## Implementation

Per the [[english-coach-training-mode-plan]]: the start script is
`english-coach/scripts/session-start.sh` and the guard lives in
`english-coach/scripts/check.sh` (inserted after `export CHECK_ENGLISH_IN_PROGRESS=1`).
The sentinel path is overridable via `CHECK_ENGLISH_SENTINEL` (also `_PROFILE`,
`_SESSIONS`, `_MISTAKE_LOG`); the staleness window is the literal `7200` seconds. The
guard additionally validates the sentinel holds a plain epoch integer (`^[0-9]+$`) before
trusting it. Both halves are covered by bash tests — see [[english-coach-testing]].

## See Also
- [[english-coach]]
- [[emma]]
- [[english-coach-memory-model]]
- [[english-coach-training-mode-design]]
- [[english-coach-training-mode-plan]]
- [[english-coach-testing]]
