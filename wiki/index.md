# Wiki Index

## Sources

- [Claude Code Plugin Command Naming Convention](sources/plugin-command-naming-convention.md) — Claude Code namespaces plugin commands as /<plugin>:<command>; command files must not repeat the plugin name
- [english-coach Training Mode — Design Spec](sources/english-coach-training-mode-design.md) — Approved design spec adding an active training mode (persona Emma) to english-coach; v1.0.0 -> 1.1.0
- [english-coach Training Mode — Implementation Plan](sources/english-coach-training-mode-plan.md) — Task-by-task TDD implementation plan for english-coach training mode (5 tasks, file structure, bash test suites, commit workflow)

## Entities

- [Emma (training-mode persona)](entities/emma.md) — Warm, casual US-native persona leading english-coach training sessions; remembers you across sessions
- [english-coach (plugin)](entities/english-coach.md) — Claude Code plugin for improving a learner's English (passive hook + active training mode)

## Concepts

- [english-coach Memory Model](concepts/english-coach-memory-model.md) — Permanent memory: profile.md, sessions.jsonl, and reused english-mistakes.jsonl
- [english-coach Testing Approach](concepts/english-coach-testing.md) — Bash-assertion test-seam pattern using CHECK_ENGLISH_* env overrides against temp dirs; the two training-mode test scripts and what they assert
- [Plugin Command Naming (no redundant prefix)](concepts/plugin-command-naming.md) — Rule: name plugin command files by action only (setup.md, stats.md) — never repeat the plugin prefix
- [Training Mode Session Lifecycle](concepts/training-mode-session-lifecycle.md) — Start/during/end protocol with pause sentinel and ordered save protocol for a training session

## Analyses

## Comparisons
