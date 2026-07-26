---
name: fanfan-russian-copy
description: Voice, register and terminology for the app's Russian user-facing copy. Use when writing or changing any user-visible string — labels, buttons, placeholders, error messages, toasts, empty states, notification and email text, manifest shortcut names. Also use when reviewing a diff that adds Russian copy, or when choosing between two ways to name a domain concept in the UI.
---

# FAN FAN Russian copy

Every user-facing string is Russian; code comments and docstrings are English.
That much is in AGENTS.md. This skill covers the part that rule does not: *which*
Russian.

The audience is teen to young-adult anime fans, on a phone, often on flaky
venue wifi, in a hurry between events — plus the organizers running the
convention on the same screens.

## Register: «ты», always

The app addresses the user informally. This is settled by usage, not taste:
`Введи адрес эл. почты`, `Введи код из письма`, `Проверь заполнение формы`,
`Укажи таймаут анонсов`, `Выбери Excel-файл для импорта`, `Попробуй ещё раз
позже`.

Two strings still use «вы» and are inconsistent, not a second convention:

- `frontend/src/routes/(app)/(protected)/feedback/+page.svelte` — `Напишите, чем хотите поделиться`
- `frontend/src/routes/(app)/(protected)/tools/broadcast/+page.svelte` — `Введите текст уведомления`

Match «ты» in new copy. Organizer-facing screens are not an exception — the
organizers are the same age group and the same people.

«Ты» does not mean sloppy: no slang, no `плз`, no memes, no exclamation marks by
default. Friendly, but composed.

## Terminology

Pick the established word. The app has drifted twice already, and a synonym
introduced now becomes the third.

| Concept | Use | Not |
| --- | --- | --- |
| The event programme | **Программа** | ~~Расписание~~ (one straggler in `tools/settings/+page.svelte:177`) |
| A single item in it | **Выступление** | ~~событие~~, ~~мероприятие~~, ~~ивент~~ |
| Voting | **Голосование** | — |
| A voting entry | **Номинация** | — |
| Notifications | **Уведомления** | ~~оповещения~~, ~~пуши~~ |
| Roles | **Участник**, **Организатор** | — |
| Feedback | **Обратная связь** | ~~фидбек~~ |

Follow the same rule for anything new: search the frontend for an existing word
before coining one.

## Tone

From `.agents/context/PRODUCT.md`: **clear, lively, calm-under-load**. The
personality lives in the color and the moments, not in the words. Concretely:

- **Say what happened and what to do.** `Нет соединения` beats `Упс! Что-то
  пошло не так 😔`.
- **No emoji in copy.** Listed in the anti-references; `kill-ai-slop` flags it.
- **No talking down.** The audience is young, not childish.
- **No corporate hedging.** `Не удалось загрузить уведомления`, not `К
  сожалению, в настоящий момент загрузка уведомлений невозможна`.
- **Errors are calm.** Con wifi drops constantly; a failed load is routine, not
  an emergency. Existing house style: `Произошла непредвиденная ошибка`,
  `Нужно войти в аккаунт заново`, `Неверный или устаревший код`.
- **Empty states teach.** A screen with nothing on it says what will appear
  there and how to make it appear.

## Mechanics

- **Ё is written** where the house style already writes it (`ещё`, `Попробуй ещё
  раз`). Stay consistent within a screen.
- **Plurals need all three forms** — 1 / 2–4 / 5+ (`минута` / `минуты` / `минут`,
  `выступление` / `выступления` / `выступлений`). A bare `+ ' мин.'` is a bug
  waiting for the number 2.
- **Use the typographic dash** `—`, not a hyphen, in prose.
- `kill-ai-slop` ships `scripts/rules.ru.mjs`, a Russian copy-tells ruleset:
  `node .agents/skills/kill-ai-slop/scripts/scan.mjs <root> --rules=.agents/skills/kill-ai-slop/scripts/rules.ru.mjs`
