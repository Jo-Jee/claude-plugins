---
title: english-coach Training Mode — Design Spec
type: source
created: 2026-07-13
updated: 2026-07-13
sources: [raw/notes/2026-07-13-english-coach-training-mode-design.md]
tags: [english-coach, design, training-mode]
---

# english-coach Training Mode — Design Spec

Approved brainstorming spec (2026-07-13) that adds an **active training mode** to the
[[english-coach]] plugin, bumping it from 1.0.0 → 1.1.0. Today the plugin is purely
passive; training mode introduces a conversational tutoring session led by a named
persona, [[emma]], who remembers past sessions.

## Summary

The existing plugin is passive: a `UserPromptSubmit` hook reviews every prompt, logs
mistakes to `~/.claude/english-mistakes.jsonl`, and `/english-coach:stats` summarizes
them. Training mode adds a slash command that opens a conversational English tutoring
session with a consistent, human-feeling persona ("Emma") who remembers past sessions
and steers natural conversation toward the learner's logged weak spots.

## Goals

- One slash command starts a tutoring session.
- The coach feels like a real, consistent person — greets by recalling last time, speaks
  casually, corrects gently in the flow of conversation.
- Permanent memory across sessions.
- Corrections during a session stay in sync with `/english-coach:stats`.
- The passive per-prompt hook does not double up with the coach during a session.

## Non-goals

- Structured curriculum / topic lessons (conversation-first instead).
- A session topic argument (deferred — command is argument-free for now).
- Any change to passive review behavior outside an active session.

## Key decisions

- **Command naming**: the plugin name already namespaces commands, so filenames must not
  repeat the prefix. Rename `commands/english-coach-stats.md` → `commands/stats.md`
  (invocation `/english-coach:stats`, body unchanged); add new `commands/train.md`
  (`/english-coach:train`). See [[english-coach]].
- **Persona**: [[emma]] — warm, casual US native-English friend; gentle inline
  corrections, never a numbered dump.
- **Memory model**: new `~/.claude/english-coach/` dir with permanent `profile.md` and
  `sessions.jsonl`; existing `english-mistakes.jsonl` reused. See
  [[english-coach-memory-model]].
- **Session lifecycle**: start via `session-start.sh` writing a pause sentinel + printing
  memory context; end via an ordered save protocol. See
  [[training-mode-session-lifecycle]].
- **Hook guard**: `check.sh` gains a sentinel guard — fresh sentinel (<2h) → stay silent;
  stale → remove and resume normal review. The 2h window governs only the sentinel,
  never memory.

## New / changed files

- `commands/stats.md` — renamed from `english-coach-stats.md` (body unchanged)
- `commands/train.md` — NEW (persona + session protocol)
- `scripts/check.sh` — CHANGED (add sentinel guard)
- `scripts/stats.sh` — unchanged
- `scripts/session-start.sh` — NEW (write sentinel + print memory context)
- `hooks/hooks.json` — unchanged
- `.claude-plugin/plugin.json` — version bump 1.0.0 → 1.1.0
- README updated to document training mode and memory files/paths.

## Testing

- `session-start.sh`: with `CHECK_ENGLISH_*` env overrides on temp paths, assert it writes
  the sentinel with an epoch timestamp and prints profile / recent sessions / category
  summary (including empty-history first-run case).
- `check.sh` sentinel guard: fresh sentinel → `exit 0` no output; stale (>2h) → removed
  and normal path; no sentinel → unchanged.
- Manual: run `/english-coach:train`, confirm Emma greets from memory, chat, say "bye",
  confirm files updated, mistake log appended, sentinel gone, passive hook resumes.

## Risks & mitigations

- **Forgotten goodbye leaves the hook muted** → 2h staleness guard auto-resumes it.
- **Model skips end-of-session save** → command body makes save protocol an explicit,
  ordered checklist; stale sentinel self-heals.
- **Mistake-log format drift** → design mandates the exact existing JSONL shape and
  category set so `stats.sh` stays uniform.

## See Also
- [[english-coach]]
- [[emma]]
- [[training-mode-session-lifecycle]]
- [[english-coach-memory-model]]
