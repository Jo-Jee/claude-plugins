# jojee-tools — Claude Code plugin marketplace

Personal Claude Code plugins by Jo-Jee.

## Plugins

### english-coach
Reviews the English in every prompt you submit. On each message it:
- lists itemized corrections (`[category] original → corrected — reason`),
- adds a full **native rewrite** when the phrasing is unnatural,
- compliments prose that already reads native,
- logs every mistake to `~/.claude/english-mistakes.jsonl`,
- exposes `/english-coach:stats` to review your history and trends, and
- adds `/english-coach:train` — an interactive tutoring session with **Emma**, a
  consistent, human-feeling coach who remembers your past sessions and steers
  conversation toward your weak spots. During a session the passive prompt-checker
  pauses (auto-resumes after 2h as a safety net) so Emma owns the feedback.

Skips slash commands, `!` bash escapes, and prompts containing fenced code blocks.

### Training-mode memory
Emma's memory lives in `~/.claude/english-coach/`:
- `profile.md` — durable facts about you and Emma's running impression.
- `sessions.jsonl` — one recap per session.

She also reads and appends to `~/.claude/english-mistakes.jsonl`, so `/english-coach:stats`
stays accurate.

**Requires:** `jq` and a `claude` binary on `PATH`.

## Install

```
/plugin marketplace add Jo-Jee/claude-plugins
/plugin install english-coach@jojee-tools
/reload-plugins
```

Then check your stats any time with `/english-coach:stats` (or `/english-coach:stats recent 20`), or start a tutoring session with `/english-coach:train`.

### Configuration (optional)
The scripts honor these env vars:
- `CHECK_ENGLISH_MISTAKE_LOG` — path to the JSONL mistake log (default `~/.claude/english-mistakes.jsonl`)
- `CHECK_ENGLISH_LOG` — debug log path (default `~/.claude/english-coach.log`)
- `CHECK_ENGLISH_CLAUDE_BIN` — override the `claude` binary used for the review

## Local development

```
claude --plugin-dir ./english-coach
```
