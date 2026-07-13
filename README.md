# jojee-tools — Claude Code plugin marketplace

Personal Claude Code plugins by Jo-Jee.

## Plugins

### english-coach
Reviews the English in every prompt you submit. On each message it:
- lists itemized corrections (`[category] original → corrected — reason`),
- adds a full **native rewrite** when the phrasing is unnatural,
- compliments prose that already reads native,
- logs every mistake to `~/.claude/english-mistakes.jsonl`, and
- exposes `/english-coach-stats` to review your history and trends.

Skips slash commands, `!` bash escapes, and prompts containing fenced code blocks.

**Requires:** `jq` and a `claude` binary on `PATH`.

## Install

```
/plugin marketplace add Jo-Jee/claude-plugins
/plugin install english-coach@jojee-tools
/reload-plugins
```

Then check your stats any time with `/english-coach-stats` (or `/english-coach-stats recent 20`).

### Configuration (optional)
The scripts honor these env vars:
- `CHECK_ENGLISH_MISTAKE_LOG` — path to the JSONL mistake log (default `~/.claude/english-mistakes.jsonl`)
- `CHECK_ENGLISH_LOG` — debug log path (default `~/.claude/english-coach.log`)
- `CHECK_ENGLISH_CLAUDE_BIN` — override the `claude` binary used for the review

## Local development

```
claude --plugin-dir ./english-coach
```
