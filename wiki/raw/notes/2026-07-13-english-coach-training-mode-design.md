# english-coach — Training Mode Design

**Date:** 2026-07-13
**Status:** Approved (brainstorming)
**Plugin:** `english-coach`

## Summary

Add an **active training mode** to the existing `english-coach` plugin. Today the plugin
is passive: a `UserPromptSubmit` hook reviews every prompt, logs mistakes to
`~/.claude/english-mistakes.jsonl`, and `/english-coach:stats` summarizes them.

Training mode adds a slash command that opens a **conversational English tutoring
session** with a consistent, named human-feeling persona ("Emma") who **remembers past
sessions** and steers natural conversation toward the learner's logged weak spots.

## Goals

- One slash command starts a tutoring session.
- The coach feels like a real, consistent person — greets you by recalling last time,
  speaks casually, corrects gently in the flow of conversation.
- The coach remembers you across sessions (permanent memory).
- Corrections during a session stay in sync with `/english-coach:stats`.
- The passive per-prompt hook does not double up with the coach during a session.

## Non-goals

- Structured curriculum / topic lessons (conversation-first instead).
- A session topic argument (deferred — command is argument-free for now).
- Any change to the passive review behavior outside of an active session.

## Command naming

The plugin is named `english-coach`, which already namespaces its commands
(`/english-coach:<name>`). Command filenames must therefore NOT repeat the prefix.

- Rename existing `commands/english-coach-stats.md` → `commands/stats.md`
  (invoked as `/english-coach:stats`).
- Add new `commands/train.md` (invoked as `/english-coach:train`).

Renaming the stats command changes only its invocation name; its body/behavior is
unchanged.

## Persona

**Emma** — a warm, casual native-English friend from the US.

- Speaks naturally: contractions, reactions, genuine follow-up questions.
- Encouraging, never robotic; never dumps a numbered list of corrections.
- Corrects gently *in the flow*: e.g. "oh — quick tip, we'd usually say *X* here", then
  keeps the conversation going.
- Greets by recalling the last session and something specific about the learner.
- Consistent identity across sessions (name, tone, manner).

## Memory model (permanent)

New directory `~/.claude/english-coach/`. The existing mistake log stays where it is.

| File | Purpose | Lifetime |
|------|---------|----------|
| `~/.claude/english-coach/profile.md` | Durable facts about the learner + Emma's running impression of level and recurring weak spots. Rewritten/updated every session. This is what makes Emma feel like she knows you. | Permanent |
| `~/.claude/english-coach/sessions.jsonl` | One recap line per completed session. | Permanent |
| `~/.claude/english-mistakes.jsonl` (existing) | Read at start for weak-spot focus; appended to during a session so `/english-coach:stats` stays accurate while the hook is paused. | Permanent |

`sessions.jsonl` record shape (one JSON object per line):

```json
{
  "ts": "2026-07-13T04:00:00Z",
  "topics": ["weekend plans", "work project"],
  "summary": "Chatted about the weekend; good flow. Struggled with article use.",
  "focus_next": ["articles", "plurals"],
  "highlights": ["Nice use of 'I'd rather'"]
}
```

Memory is unbounded — Emma reads it however old it is.

## Session lifecycle

### 1. Start (`/english-coach:train`)

The command markdown runs `scripts/session-start.sh` in its `!`-prefixed preamble. The
script:

1. Creates the pause sentinel `~/.claude/english-coach/.session-active` containing the
   current epoch seconds.
2. Prints the learner's memory into the command context:
   - full `profile.md` (if present),
   - the last ~3 lines of `sessions.jsonl`,
   - a top-categories summary from `english-mistakes.jsonl` (reuse the logic style of
     `stats.sh`).

The command body then instructs Emma to open with a natural, personalized greeting that
references the last session, and to ease into conversation while steering toward the
learner's weak spots.

### 2. During

- Natural conversation. Gentle inline corrections only.
- Emma keeps a running mental note of notable mistakes to persist at the end.
- The passive hook stays paused (see hook change).

### 3. End

Triggered when the learner signals they want to stop (e.g. "bye", "let's stop"), or Emma
wraps up. Emma performs the save protocol (using Write/Edit + Bash/append):

1. Append a recap object to `~/.claude/english-coach/sessions.jsonl`.
2. Update `~/.claude/english-coach/profile.md` with any new durable facts and an updated
   impression.
3. Append notable corrections made during the session to
   `~/.claude/english-mistakes.jsonl`, using the **exact** existing JSONL shape
   (`ts, category, original, corrected, reason, context`) so `stats.sh` reads them
   uniformly. Category must be one of the existing categories used by `check.sh`.
4. Remove the sentinel `~/.claude/english-coach/.session-active`.
5. Say a warm goodbye.

## Hook change (`scripts/check.sh`)

Add a guard near the top (after the recursion guard, before the LLM call). Pseudocode:

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

- The 2h window governs ONLY the sentinel, never memory.
- Slash commands already `exit 0` earlier in `check.sh`, so `/english-coach:train` itself
  is never reviewed; the guard covers the normal prompts typed *during* the session.
- Path is overridable for tests via an env var consistent with the existing
  `CHECK_ENGLISH_*` convention (e.g. `CHECK_ENGLISH_SENTINEL`).

## New / changed files

```
english-coach/
  commands/
    stats.md          # renamed from english-coach-stats.md (body unchanged)
    train.md          # NEW — persona + session protocol
  scripts/
    check.sh          # CHANGED — add sentinel guard
    stats.sh          # unchanged
    session-start.sh  # NEW — write sentinel + print memory context
  hooks/hooks.json    # unchanged
  .claude-plugin/plugin.json  # version bump 1.0.0 → 1.1.0
```

README updated to document training mode and the new memory files/paths.

## Testing

- `session-start.sh`: with `CHECK_ENGLISH_*` env overrides pointing at temp paths,
  assert it writes the sentinel with an epoch timestamp and prints profile / recent
  sessions / category summary (including the empty-history first-run case).
- `check.sh` sentinel guard: fresh sentinel → `exit 0` with no output; stale (>2h)
  sentinel → removed and normal path taken; no sentinel → unchanged behavior. Reuse the
  env-override pattern already in the script.
- Manual: run `/english-coach:train`, confirm Emma greets using memory, hold a short
  chat, say "bye", confirm `sessions.jsonl` + `profile.md` updated, mistake log appended,
  sentinel gone, and the passive hook resumes on the next normal prompt.

## Risks & mitigations

- **Forgotten goodbye leaves the hook muted** → 2h staleness guard auto-resumes it.
- **Model skips the end-of-session save** → the command body makes the save protocol an
  explicit, ordered checklist; a stale sentinel still self-heals.
- **Mistake-log format drift** → design mandates the exact existing JSONL shape and
  category set so `stats.sh` stays uniform.
```