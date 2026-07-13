# english-coach Training Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an interactive, memory-backed conversational tutoring mode ("Emma") to the `english-coach` plugin, invoked by `/english-coach:train`.

**Architecture:** A prompt-driven slash command carries the persona and session protocol. A `session-start.sh` helper drops a pause-sentinel and prints the learner's memory into context; the model (Emma) converses and, at session end, persists a recap/profile/mistakes and removes the sentinel. The passive `check.sh` hook gains a guard that stays silent while a fresh sentinel exists.

**Tech Stack:** Bash, `jq`, Claude Code plugin command markdown. Tests are Bash assertion scripts using `CHECK_ENGLISH_*` env overrides against temp paths (matching the existing scripts' test-seam convention).

## Global Constraints

- Plugin commands are namespaced under `english-coach`; command filenames must NOT repeat the prefix (files: `stats.md`, `train.md`).
- Mistake log entries MUST use the exact existing JSONL shape: `{ts, category, original, corrected, reason, context}`.
- Mistake `category` MUST be one of: `articles, agreement, tense, prepositions, capitalization, plurals, spelling, word-choice, word-order, contractions, punctuation, structure, other` (plus `rewrite` for full native rewrites, as `check.sh` uses).
- All new file paths overridable via env vars following the existing `CHECK_ENGLISH_*` convention.
- Sentinel staleness window is exactly `7200` seconds (2h). This governs the sentinel ONLY, never memory.
- Default paths: sentinel `~/.claude/english-coach/.session-active`, profile `~/.claude/english-coach/profile.md`, sessions `~/.claude/english-coach/sessions.jsonl`, mistake log `~/.claude/english-mistakes.jsonl` (existing).

---

## File Structure

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
    test-session-start.sh  # NEW
    test-check-sentinel.sh # NEW
  .claude-plugin/plugin.json  # MODIFY — version 1.0.0 -> 1.1.0
README.md                     # MODIFY — document training mode
```

---

### Task 1: `session-start.sh` — write sentinel and print memory context

**Files:**
- Create: `english-coach/scripts/session-start.sh`
- Test: `english-coach/tests/test-session-start.sh`

**Interfaces:**
- Consumes: env overrides `CHECK_ENGLISH_SENTINEL`, `CHECK_ENGLISH_PROFILE`, `CHECK_ENGLISH_SESSIONS`, `CHECK_ENGLISH_MISTAKE_LOG`.
- Produces: writes epoch seconds to the sentinel file; prints a markdown memory block to stdout containing sections `## Your learner profile`, `## Recent sessions`, `## Top mistake categories`.

- [ ] **Step 1: Write the failing test**

Create `english-coach/tests/test-session-start.sh`:

```bash
#!/usr/bin/env bash
# Tests for session-start.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/session-start.sh"
fail=0
assert() { # desc, condition already evaluated -> $1 desc, $2 = 0/1 result
  if [ "$2" -ne 0 ]; then echo "FAIL: $1"; fail=1; else echo "ok: $1"; fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export CHECK_ENGLISH_SENTINEL="$TMP/ec/.session-active"
export CHECK_ENGLISH_PROFILE="$TMP/ec/profile.md"
export CHECK_ENGLISH_SESSIONS="$TMP/ec/sessions.jsonl"
export CHECK_ENGLISH_MISTAKE_LOG="$TMP/mistakes.jsonl"

# --- Case 1: first run, no memory files exist ---
out="$(bash "$SCRIPT")"
[ -f "$CHECK_ENGLISH_SENTINEL" ]; assert "sentinel created" $?
grep -Eq '^[0-9]+$' "$CHECK_ENGLISH_SENTINEL"; assert "sentinel holds epoch seconds" $?
printf '%s' "$out" | grep -q "## Your learner profile"; assert "profile section printed" $?
printf '%s' "$out" | grep -q "## Recent sessions"; assert "sessions section printed" $?
printf '%s' "$out" | grep -q "## Top mistake categories"; assert "mistakes section printed" $?
printf '%s' "$out" | grep -qi "first session"; assert "first-run note shown" $?

# --- Case 2: with memory present ---
mkdir -p "$TMP/ec"
printf 'George is a Korean SWE. Weak on articles.\n' > "$CHECK_ENGLISH_PROFILE"
printf '{"ts":"2026-07-10T00:00:00Z","topics":["weekend"],"summary":"good flow","focus_next":["articles"],"highlights":[]}\n' > "$CHECK_ENGLISH_SESSIONS"
printf '{"ts":"2026-07-10T00:00:00Z","category":"articles","original":"a","corrected":"the","reason":"x","context":"y"}\n' > "$CHECK_ENGLISH_MISTAKE_LOG"
printf '{"ts":"2026-07-10T00:01:00Z","category":"articles","original":"b","corrected":"c","reason":"x","context":"y"}\n' >> "$CHECK_ENGLISH_MISTAKE_LOG"
out="$(bash "$SCRIPT")"
printf '%s' "$out" | grep -q "Korean SWE"; assert "profile contents printed" $?
printf '%s' "$out" | grep -q "good flow"; assert "recent session summary printed" $?
printf '%s' "$out" | grep -Eq "articles.*2|2.*articles"; assert "category count printed" $?

[ "$fail" -eq 0 ] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash english-coach/tests/test-session-start.sh`
Expected: FAIL (script does not exist yet — `bash: .../session-start.sh: No such file`).

- [ ] **Step 3: Write the implementation**

Create `english-coach/scripts/session-start.sh`:

```bash
#!/usr/bin/env bash
# Slash-command preamble for /english-coach:train.
# 1. Drops the pause sentinel so the passive check.sh hook stays quiet during the session.
# 2. Prints the learner's memory (profile, recent sessions, top mistake categories) to
#    stdout so it lands in the command context and Emma can greet the learner knowingly.
# Paths are env-overridable for testing, following the existing CHECK_ENGLISH_* convention.

SENTINEL="${CHECK_ENGLISH_SENTINEL:-$HOME/.claude/english-coach/.session-active}"
PROFILE="${CHECK_ENGLISH_PROFILE:-$HOME/.claude/english-coach/profile.md}"
SESSIONS="${CHECK_ENGLISH_SESSIONS:-$HOME/.claude/english-coach/sessions.jsonl}"
MISTAKE_LOG="${CHECK_ENGLISH_MISTAKE_LOG:-$HOME/.claude/english-mistakes.jsonl}"

mkdir -p "$(dirname "$SENTINEL")" "$(dirname "$PROFILE")" "$(dirname "$SESSIONS")" 2>/dev/null

# Mark the session active (epoch seconds — check.sh compares against a 2h window).
date +%s > "$SENTINEL"

echo "## Your learner profile"
if [ -s "$PROFILE" ]; then
  cat "$PROFILE"
else
  echo "(no profile yet — this is your first session with them)"
fi
echo ""

echo "## Recent sessions"
if [ -s "$SESSIONS" ]; then
  tail -n 3 "$SESSIONS" | jq -r '"- \(.ts // "?"): \(.summary // "(no summary)") [focus next: \((.focus_next // []) | join(", "))]"'
else
  echo "(none yet)"
fi
echo ""

echo "## Top mistake categories"
if [ -s "$MISTAKE_LOG" ]; then
  jq -r '.category' "$MISTAKE_LOG" | sort | uniq -c | sort -rn | head -n 5 \
    | awk '{printf "- %s (%s)\n", $2, $1}'
else
  echo "(no mistakes logged yet)"
fi
```

Then make it executable: `chmod +x english-coach/scripts/session-start.sh`.

- [ ] **Step 4: Run test to verify it passes**

Run: `bash english-coach/tests/test-session-start.sh`
Expected: `ALL PASS`.

- [ ] **Step 5: Commit**

```bash
chmod +x english-coach/scripts/session-start.sh english-coach/tests/test-session-start.sh
git add english-coach/scripts/session-start.sh english-coach/tests/test-session-start.sh
git commit -m "feat(english-coach): add session-start.sh for training mode"
```

---

### Task 2: `check.sh` — pause while a fresh session sentinel exists

**Files:**
- Modify: `english-coach/scripts/check.sh` (insert guard after the recursion guard block)
- Test: `english-coach/tests/test-check-sentinel.sh`

**Interfaces:**
- Consumes: env override `CHECK_ENGLISH_SENTINEL`; existing `CHECK_ENGLISH_CLAUDE_BIN`, `CHECK_ENGLISH_MISTAKE_LOG`, `CHECK_ENGLISH_LOG`.
- Produces: exits `0` with no stdout when a fresh (<7200s) sentinel exists; removes a stale sentinel and proceeds normally otherwise.

- [ ] **Step 1: Write the failing test**

Create `english-coach/tests/test-check-sentinel.sh`:

```bash
#!/usr/bin/env bash
# Tests for the sentinel guard in check.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/check.sh"
fail=0
assert() { if [ "$2" -ne 0 ]; then echo "FAIL: $1"; fail=1; else echo "ok: $1"; fi; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Stub `claude` so the non-paused path returns quickly with "OK".
STUB="$TMP/claude"
printf '#!/usr/bin/env bash\necho OK\n' > "$STUB"
chmod +x "$STUB"

export CHECK_ENGLISH_CLAUDE_BIN="$STUB"
export CHECK_ENGLISH_MISTAKE_LOG="$TMP/mistakes.jsonl"
export CHECK_ENGLISH_LOG="$TMP/debug.log"
export CHECK_ENGLISH_SENTINEL="$TMP/.session-active"

PROMPT_JSON='{"prompt":"i has a apple"}'

# --- Case 1: fresh sentinel -> silent, sentinel preserved ---
date +%s > "$CHECK_ENGLISH_SENTINEL"
out="$(printf '%s' "$PROMPT_JSON" | bash "$SCRIPT")"
[ -z "$out" ]; assert "fresh sentinel -> no output" $?
[ -f "$CHECK_ENGLISH_SENTINEL" ]; assert "fresh sentinel preserved" $?

# --- Case 2: stale sentinel (>2h) -> proceeds, sentinel removed ---
echo $(( $(date +%s) - 8000 )) > "$CHECK_ENGLISH_SENTINEL"
out="$(printf '%s' "$PROMPT_JSON" | bash "$SCRIPT")"
[ -n "$out" ]; assert "stale sentinel -> produces output" $?
[ ! -f "$CHECK_ENGLISH_SENTINEL" ]; assert "stale sentinel removed" $?

# --- Case 3: no sentinel -> normal behavior ---
rm -f "$CHECK_ENGLISH_SENTINEL"
out="$(printf '%s' "$PROMPT_JSON" | bash "$SCRIPT")"
[ -n "$out" ]; assert "no sentinel -> produces output" $?

[ "$fail" -eq 0 ] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash english-coach/tests/test-check-sentinel.sh`
Expected: FAIL on "fresh sentinel -> no output" (guard not present yet; the stub returns "OK" → a compliment is printed).

- [ ] **Step 3: Add the guard to `check.sh`**

In `english-coach/scripts/check.sh`, immediately after the recursion-guard block (the line `export CHECK_ENGLISH_IN_PROGRESS=1`), insert:

```bash

# Training-mode pause: while a fresh session sentinel exists, stay silent so the
# interactive coach (/english-coach:train) owns all feedback. A sentinel older than
# 2h is treated as an abandoned session (forgotten goodbye) — remove it and resume.
SENTINEL="${CHECK_ENGLISH_SENTINEL:-$HOME/.claude/english-coach/.session-active}"
if [ -f "$SENTINEL" ]; then
  started=$(cat "$SENTINEL" 2>/dev/null)
  now=$(date +%s)
  if printf '%s' "$started" | grep -Eq '^[0-9]+$' && [ $((now - started)) -ge 0 ] && [ $((now - started)) -lt 7200 ]; then
    exit 0
  fi
  rm -f "$SENTINEL"
fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash english-coach/tests/test-check-sentinel.sh`
Expected: `ALL PASS`.

- [ ] **Step 5: Commit**

```bash
chmod +x english-coach/tests/test-check-sentinel.sh
git add english-coach/scripts/check.sh english-coach/tests/test-check-sentinel.sh
git commit -m "feat(english-coach): pause passive hook during training sessions"
```

---

### Task 3: Rename stats command to drop redundant prefix

**Files:**
- Rename: `english-coach/commands/english-coach-stats.md` → `english-coach/commands/stats.md` (body unchanged)

**Interfaces:**
- Produces: command invocation `/english-coach:stats` (was `/english-coach:english-coach-stats`).

- [ ] **Step 1: Rename via git**

```bash
git mv english-coach/commands/english-coach-stats.md english-coach/commands/stats.md
```

- [ ] **Step 2: Verify body is unchanged and still references stats.sh**

Run: `grep -q 'scripts/stats.sh' english-coach/commands/stats.md && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add -A english-coach/commands/
git commit -m "refactor(english-coach): rename stats command to drop redundant prefix"
```

---

### Task 4: `train.md` — the training-mode slash command

**Files:**
- Create: `english-coach/commands/train.md`

**Interfaces:**
- Consumes: `session-start.sh` output (via `!` preamble); the memory files at their default paths.
- Produces: command `/english-coach:train`.

- [ ] **Step 1: Write the command file**

Create `english-coach/commands/train.md` with exactly this content:

````markdown
---
description: Start a spoken-style English tutoring session with Emma, who remembers your past sessions
allowed-tools: Bash, Read, Write, Edit
---
You are now **Emma**, the user's English coach and conversation partner — not the usual assistant. Stay fully in character as Emma for this whole session.

## Who Emma is
- A warm, casual native-English-speaking friend from the US.
- Speaks naturally: contractions, genuine reactions, real follow-up questions.
- Encouraging and human — never robotic, never a numbered lecture.
- Remembers the user across sessions and greets them by recalling last time.

## The memory below is what you remember about this learner
!`"${CLAUDE_PLUGIN_ROOT}/scripts/session-start.sh"`

## How to run the session
1. **Open** with a natural, personalized greeting. Reference the last session or a
   specific fact from the profile above (if this is the first session, warmly introduce
   yourself and ask a little about them). Then start a real conversation.
2. **Converse** naturally. Ask questions, react, keep it flowing.
3. **Correct gently, in the flow.** When they make a mistake, don't dump a list — weave it
   in: "oh — quick tip, we'd usually say *X* here 🙂" then continue. Prioritize their known
   weak spots from the memory above.
4. **Keep a running mental note** of the notable mistakes you correct — you'll save them at
   the end.

## Ending the session
When the learner signals they want to stop (e.g. "bye", "let's stop", "that's it for
today"), OR you sense a natural end, do ALL of the following, then say a warm goodbye:

1. **Append a session recap** to `~/.claude/english-coach/sessions.jsonl` — one JSON object
   on a single line. Use this shape and fill it from the real session:
   ```
   jq -nc --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
     '{ts:$ts, topics:["<topics you covered>"], summary:"<1-2 sentence recap>", focus_next:["<categories to work on next>"], highlights:["<things they did well>"]}' \
     >> ~/.claude/english-coach/sessions.jsonl
   ```
2. **Update** `~/.claude/english-coach/profile.md` (create if missing) with any new durable
   facts about them and your updated impression of their level and recurring weak spots.
   Keep it concise — it is your long-term memory of this person.
3. **Append notable corrections** to `~/.claude/english-mistakes.jsonl`, one JSON object per
   line, using EXACTLY this shape so the stats command reads them uniformly:
   ```
   {"ts":"<ISO-8601 UTC>","category":"<one category>","original":"<what they wrote>","corrected":"<the fix>","reason":"<brief>","context":"<the sentence>"}
   ```
   `category` MUST be one of: articles, agreement, tense, prepositions, capitalization,
   plurals, spelling, word-choice, word-order, contractions, punctuation, structure, other.
4. **Remove the session sentinel** so the passive checker resumes:
   ```
   rm -f ~/.claude/english-coach/.session-active
   ```
5. Say goodbye as Emma, and mention you'll remember this next time.

If the learner types a slash command or clearly wants to leave the session abruptly, still
run the ending steps (at least remove the sentinel) before stopping.
````

- [ ] **Step 2: Verify frontmatter and preamble parse**

Run: `head -4 english-coach/commands/train.md` and confirm the YAML frontmatter block is intact and `session-start.sh` is referenced in a `!` preamble.
Expected: frontmatter with `description` and `allowed-tools`, and the `!`-prefixed script reference present.

- [ ] **Step 3: Commit**

```bash
git add english-coach/commands/train.md
git commit -m "feat(english-coach): add /english-coach:train conversational tutoring command"
```

---

### Task 5: Version bump + README

**Files:**
- Modify: `english-coach/.claude-plugin/plugin.json` (`1.0.0` → `1.1.0`)
- Modify: `README.md` (document training mode)

**Interfaces:** none (docs/metadata only).

- [ ] **Step 1: Bump the plugin version**

In `english-coach/.claude-plugin/plugin.json`, change `"version": "1.0.0"` to `"version": "1.1.0"`.

- [ ] **Step 2: Update README**

In `README.md`, under the `english-coach` section, add a training-mode subsection describing:
- `/english-coach:train` starts a conversational session with Emma who remembers past sessions;
- the passive hook pauses during a session (2h staleness safety net);
- new memory files: `~/.claude/english-coach/profile.md` and `~/.claude/english-coach/sessions.jsonl`;
- update the stats command reference from `/english-coach-stats` to `/english-coach:stats`.

Concretely, replace the stats bullet/line and append:

```markdown
- exposes `/english-coach:stats` to review your history and trends, and
- adds `/english-coach:train` — an interactive tutoring session with **Emma**, a
  consistent, human-feeling coach who remembers your past sessions and steers
  conversation toward your weak spots. During a session the passive prompt-checker
  pauses (auto-resumes after 2h as a safety net) so Emma owns the feedback.

### Training-mode memory
Emma's memory lives in `~/.claude/english-coach/`:
- `profile.md` — durable facts about you and Emma's running impression.
- `sessions.jsonl` — one recap per session.

She also reads and appends to `~/.claude/english-mistakes.jsonl`, so `/english-coach:stats`
stays accurate.
```

- [ ] **Step 3: Verify JSON is valid**

Run: `jq . english-coach/.claude-plugin/plugin.json >/dev/null && echo OK`
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add english-coach/.claude-plugin/plugin.json README.md
git commit -m "docs(english-coach): document training mode; bump to 1.1.0"
```

---

## Self-Review

**Spec coverage:**
- Command naming (stats.md rename + train.md) → Tasks 3, 4. ✓
- Persona "Emma" → Task 4. ✓
- Memory model (profile.md, sessions.jsonl, reuse mistake log) → Tasks 1, 4. ✓
- Session lifecycle start (sentinel + context print) → Task 1. ✓
- Session lifecycle during/end (save protocol) → Task 4. ✓
- `check.sh` sentinel guard w/ 2h staleness → Task 2. ✓
- Version bump + README → Task 5. ✓
- Testing (session-start, check.sh guard) → Tasks 1, 2 (bash assertion scripts). ✓

**Placeholder scan:** Command-body angle-bracket fields (`<topics you covered>`, etc.) are intentional instructions for the model at runtime, not plan placeholders — all script/test/code content is concrete. ✓

**Type/name consistency:** Env var names (`CHECK_ENGLISH_SENTINEL/PROFILE/SESSIONS/MISTAKE_LOG`), sentinel path, and JSONL shape are identical across Tasks 1, 2, 4. Staleness window `7200` consistent. ✓
