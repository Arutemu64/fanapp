# FestEngine webhooks

FestEngine sends stage events to fanapp, and fanapp updates the schedule from
them. The reasons for the design are in
[ADR-0048](adr/0048-festengine-webhooks.md).

## Setup

1. In FestEngine's settings, press **Generate** next to the webhook secret. Set
   the URL to `https://<site>/api/webhooks/festengine`.
2. Put the same secret in fanapp's `.env` as `FESTENGINE__WEBHOOK_SECRET` and
   restart the API.
3. In FestEngine, press **Send test event**. You should get `200` with the body
   `{"status": "ignored", "actions": []}`. A `404` means the secret or the
   server clock is off: the timestamp must be within 5 minutes.
4. Before the convention, compare a real export from both sides. FestEngine's
   `num` comes from filenames, fanapp's `number` from the schedule import. Both
   must be the Cosplay2 request number.

To turn it off, unset the secret (the endpoint then answers 404), or revoke
`schedule:manage` from the system user.

## Contract

`POST /api/webhooks/festengine`, signed per
[Standard Webhooks](https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md).
The receiver reads these headers: `webhook-id`, `webhook-timestamp` and
`webhook-signature` (one or more `v1,<base64>` separated by spaces). The body is
JSON:

```json
{
  "type": "row.updated",
  "timestamp": "2026-10-09T09:12:40.003Z",
  "data": {
    "num": "183",
    "row_type": "track",
    "notes": ">305 maybe",
    "previous": { "notes": "" }
  }
}
```

fanapp reads only the fields shown and ignores the rest. Any other `type` gets
`ignored`.

| Event                                                   | fanapp does                                                                        |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `row.show`, `row.play` with `row_type` `track` or `dup` | Sets act `num` current. A cue older than 60 s answers `stale` and changes nothing. |
| `row.updated` on a `track` row with `previous.notes`    | Diffs the notes (below), then skips or unskips, then moves or unmoves.             |

`num` is read up to its first non-digit: `"007"` is 7, `"305a"` is 305, and
`"brk"` is ignored.

### Notes syntax

An action fires only when a marker differs between the old and the new note.

| Change                                            | Action                                                                     |
| ------------------------------------------------- | -------------------------------------------------------------------------- |
| First character becomes `-`                       | Skip                                                                       |
| First character stops being `-`                   | Unskip                                                                     |
| `>NNN` appears or changes (`>305`, `>305a maybe`) | Move after act NNN, or after the closest lower number if NNN doesn't exist |
| `>NNN` disappears                                 | Unmove, if FestEngine made the act's last move                             |

A `-` anywhere but first ("2-3 min") is plain text. `>NNN` needs three digits
and uses FestEngine's regex, `>(\d{3}(\w)?)([^\w].*)?`.

### Responses

FestEngine reads only the status code. It retries on 429 and 5xx and drops every
other error.

| Status                                                               | When                                                                                                                 |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `200 {"status": "updated", "actions": [...]}`                        | Something changed. Actions: `set_current`, `skip`, `unskip`, `move`, `unmove`.                                       |
| `200 {"status": "unchanged" \| "ignored" \| "stale", "actions": []}` | Nothing to do.                                                                                                       |
| `400`                                                                | A schedule rule refused it: `CURRENT_EVENT_NOT_ALLOWED`, `SKIPPED_EVENT_NOT_ALLOWED`, `SAME_EVENTS_ARE_NOT_ALLOWED`. |
| `403`                                                                | The system user lacks `schedule:manage`.                                                                             |
| `404`                                                                | Bad or missing signature, no secret configured, or `EVENT_NOT_FOUND` (unknown act number).                           |
| `422`                                                                | The body is signed but malformed.                                                                                    |
| `429` + `Retry-After`                                                | Announcement cooldown. A note that both skips and moves (`->305`) gets this on the move, and the retry finishes it.  |

## Памятка оператору FestEngine

- `-` в начале заметки снимает номер. Уберите `-`, и номер вернётся.
- `>305` в заметке переносит номер после 305-го. Сотрите `>305`, и номер
  встанет на прежнее место, если его с тех пор не переносили в приложении.
- F1 или F2 делают номер текущим в приложении.
- На репетиции держите **Send Webhooks** выключенным, иначе зрителям уйдут
  уведомления.
- Ошиблись? Исправьте расписание в приложении. Уже отправленное уведомление
  отозвать нельзя.
