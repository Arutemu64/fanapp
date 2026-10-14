# FAN FAN companion app

Companion web app for the FAN FAN anime convention: visitors follow the programme, vote and get notified; organizers run the programme and message visitors.

## Programme

**Entry**:
One row of the programme, in order: an event or a block start.
_Avoid_: Row, item

**Event**:
An entry for something on stage — an act, a break, the opening. Only events are numbered, timed, queued, made current, skipped, moved or subscribed to. The screens call one «выступление».
_Avoid_: Performance, act (in code)

**Block**:
A titled section of the programme: a block start and every event after it up to the next block start. An event's block is wherever it sits, so moving it across a block start moves it into that block.
_Avoid_: Section, group

## Notifications

**Notification**:
One message for one user, shown in their in-app feed and delivered to each channel they can be reached on.
_Avoid_: Message, alert

**Mailing**:
One send of a notification to many users at once, which is tracked, counted and can be cancelled as a whole. The English name is a calque of «рассылка», the word the organizers' screens use.
_Avoid_: Campaign, batch, dispatch, mail (it is never email)

**Broadcast**:
A mailing an organizer writes by hand for every user holding the chosen roles. The other kind of mailing is the automatic one a schedule change sends, so "broadcast" never names a mailing in general.
_Avoid_: Announcement

**Channel**:
A route a notification reaches a user by outside the app: Telegram, VK or Web Push.
_Avoid_: Provider, transport
