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

- **Frontend copy lives in `frontend/messages/ru.json`**, used as `m.key()` from
  `#lib/paraglide/messages.js` (Paraglide JS, ADR-0027). Edit the JSON, not a
  string literal in a component.

- **Plurals need all three forms** — 1 / 2–4 / 5+ (`минута` / `минуты` / `минут`,
  `выступление` / `выступления` / `выступлений`). A bare `+ ' мин.'` is a bug
  waiting for the number 2. Frontend: a plural message in `frontend/messages/ru.json`
  (`declarations` + `plural` selector; copy `votes_count`).
  Jinja: the `plural` filter, `{{ n|plural('минуту', 'минуты', 'минут') }}`
  (registered in `adapters/jinja/factory.py`).
- **Ё is written always** (`ещё`, `её`, `всё`, `учёт`) — see `redpolitika.md`.
- **Use the typographic dash** `—`, not a hyphen, in prose, and bind it to the
  word before with a non-breaking space so a wrapped line never opens with a
  dash: `&nbsp;—` in markup and attribute strings, `\u00A0—` in a JS string
  (never a literal U+00A0, which is invisible in review).
- **Each email is two files**, an HTML template and a `.txt.jinja2` plain-text
  alternative (`email_login_code`, `email_confirmation_code`). Change the copy in
  both, or the two halves of one message disagree — and render them before
  calling it done, per AGENTS.md.
- **Copy-tells scan.** Russian AI-copywriting tells (marketing-speak and
  «не просто X — это Y»). Every hit is a lead to read, not a verdict, and a clean
  run prints nothing. Run from the repo root:
  ```sh
  grep -rniE 'не просто .{1,40}[—–-] *это|попрощайтесь с|забудьте о том|представьте себе мир|молниеносн|бесшовн|безупречн|революционн|беспрецедентн|раскройте (весь )?потенциал|на новый уровень|в считанные секунды' frontend/messages/ru.json backend/src/fanfan/adapters/jinja/templates
  ```
  `antislop-copywriting` covers the English-shaped patterns (rule of three,
  signposting, chatbot closers) that also show up in translated copy.
