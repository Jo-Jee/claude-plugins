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
