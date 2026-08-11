---
name: fanfan-russian-copy
description: Repo mechanics for the app's Russian user-facing copy — plural forms, ё, two-file emails, the copy-tells scanner. Use when writing or changing any user-visible string — labels, buttons, placeholders, error messages, toasts, empty states, notification and email text, manifest shortcut names. Voice, register and terminology live in .agents/redpolitika.md (read automatically by the ux-copy / redaktura skills); this skill covers only what those don't.
---

# FAN FAN Russian copy — mechanics

Every user-facing string is Russian; code comments and docstrings are English.
That much is in AGENTS.md.

**Voice, register and terminology live in [`.agents/redpolitika.md`](../../../.agents/redpolitika.md)** —
the «ты» register, the gender-agreement trap in past-tense forms, the glossary
(Программа / Выступление / Голосование / …), the tone (`clear, lively,
calm-under-load`), the no-exclamation-by-default and always-ё rules, and the
naming `ФАН ФАН`. The vendored `ux-copy` and `redaktura` skills read that file
automatically before writing or editing copy; load `ux-copy` for interface
strings. Update `redpolitika.md` (via the `redpolitika` skill) when the voice or
glossary changes — not this file.

This skill covers only the repo mechanics those skills can't know:

- **Plurals need all three forms** — 1 / 2–4 / 5+ (`минута` / `минуты` / `минут`,
  `выступление` / `выступления` / `выступлений`). A bare `+ ' мин.'` is a bug
  waiting for the number 2. Frontend: `pluralize()` in `lib/utils/formatters.ts`.
  Jinja: the `events_pluralize` macro pattern in the notification templates.
- **Ё is written always** (`ещё`, `её`, `всё`, `учёт`) — see `redpolitika.md`.
- **Use the typographic dash** `—`, not a hyphen, in prose.
- **Each email is two files**, an HTML template and a `.txt.jinja2` plain-text
  alternative (`email_login_code`, `email_confirmation_code`). Change the copy in
  both, or the two halves of one message disagree — and render them before
  calling it done, per AGENTS.md.
- `kill-ai-slop` ships `scripts/rules.ru.mjs`, a Russian copy-tells ruleset:
  `node .agents/skills/kill-ai-slop/scripts/scan.mjs <root> --rules=.agents/skills/kill-ai-slop/scripts/rules.ru.mjs`
