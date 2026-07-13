---
title: english-coach Memory Model
type: concept
created: 2026-07-13
updated: 2026-07-13
sources: [raw/notes/2026-07-13-english-coach-training-mode-design.md]
tags: [english-coach, memory]
---

# english-coach Memory Model

The permanent memory that lets [[emma]] feel like she knows the learner across
[[training-mode-session-lifecycle|sessions]]. Training mode adds a new directory
`~/.claude/english-coach/`; the existing mistake log stays where it is.

## Files

| File | Purpose | Lifetime |
|------|---------|----------|
| `~/.claude/english-coach/profile.md` | Durable facts about the learner + Emma's running impression of level and recurring weak spots. Rewritten/updated every session. This is what makes Emma feel like she knows you. | Permanent |
| `~/.claude/english-coach/sessions.jsonl` | One recap line per completed session. | Permanent |
| `~/.claude/english-mistakes.jsonl` (existing) | Read at start for weak-spot focus; appended to during a session so `/english-coach:stats` stays accurate while the hook is paused. | Permanent |

Memory is **unbounded** — Emma reads it however old it is. (Note: the 2h staleness window
in the [[training-mode-session-lifecycle|sentinel guard]] governs only the pause sentinel,
never memory.)

## `sessions.jsonl` record shape

```json
{
  "ts": "2026-07-13T04:00:00Z",
  "topics": ["weekend plans", "work project"],
  "summary": "Chatted about the weekend; good flow. Struggled with article use.",
  "focus_next": ["articles", "plurals"],
  "highlights": ["Nice use of 'I'd rather'"]
}
```

## Reuse of `english-mistakes.jsonl`

The training session must append corrections in the **exact existing JSONL shape**
(`ts, category, original, corrected, reason, context`), with `category` drawn from the
category set used by `check.sh`, so that `stats.sh` / `/english-coach:stats` continues to
read all entries uniformly whether they came from the passive hook or a training session.

## Implementation

Per the [[english-coach-training-mode-plan]], the three files are read at session start by
`session-start.sh` and written at session end by the `train.md` save protocol. Their paths
are env-overridable for testing — `CHECK_ENGLISH_PROFILE`, `CHECK_ENGLISH_SESSIONS`,
`CHECK_ENGLISH_MISTAKE_LOG` — see [[english-coach-testing]].

## See Also
- [[english-coach]]
- [[emma]]
- [[training-mode-session-lifecycle]]
- [[english-coach-training-mode-design]]
- [[english-coach-training-mode-plan]]
- [[english-coach-testing]]
