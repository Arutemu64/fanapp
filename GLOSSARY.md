# FAN FAN companion app

Companion web app for the FAN FAN anime convention: visitors follow the schedule, vote and get notified; organizers run the schedule and message visitors.

## Roles

**Role**:
What a user is at the festival. Every user holds exactly one; broadcasts are addressed by role, and a ticket carries the role its holder gets. Beyond the organizer role opening the organizer tools, a role lets a user do nothing by itself.
_Avoid_: Group, user type

**Permission**:
One organizer power, such as managing the schedule or sending broadcasts, granted to a user one by one and independent of their role.
_Avoid_: Right, access, role

**Guest**:
Someone using the app without signing in. A guest holds no role and is not a user.
_Avoid_: Anonymous, visitor

**Visitor**:
A user who came to watch, the role every new account starts with. The screens call one «зритель».
_Avoid_: «Гость» (at a convention it means an invited star), attendee

**Participant**:
Someone who performs at the festival. The same person holds the participant role and is a voting entry in a nomination. The screens call one «участник».
_Avoid_: Performer, contestant, cosplayer

**Volunteer**:
A user who helps run the festival on site. The screens call one «волонтёр».
_Avoid_: Helper

**Organizer**:
A user who runs the festival. The screens call one «организатор».
_Avoid_: Org, organiser, admin

**Staff**:
Volunteers and organizers together: the people running the festival rather than visiting it.
_Avoid_: Crew, team

**User number**:
A user's permanent six-digit number, drawn at random when the account is created, by which staff find the user in person — read aloud or scanned from the quest QR code. It is not secret and not an access credential. The screens call it «ID пользователя», or «ID» where the context is already clear.
_Avoid_: Public ID, participant number, «номер участника», bare «номер»

## Schedule

**Schedule**:
The running order of everything on the festival stage. The screens call it «программа».
_Avoid_: Programme, timetable, lineup

**Entry**:
One row of the schedule, in order: an event or a block start.
_Avoid_: Row, item

**Event**:
An entry for something on stage — an act, a break, the opening. Only events are numbered, timed, given a position, made current, skipped, moved or subscribed to. The screens call one «выступление».
_Avoid_: Performance, act (in code)

**Position**:
An event's place in the running order, 1..N, counting only events that are not skipped. "Осталось N выступлений" counts positions, and so does a reminder's two-act floor.
_Avoid_: Queue

**Changeover**:
The pause between two events while one group leaves the stage and the next walks on. Planned durations leave it out, so the wait estimate adds an organizer-set average after each event. The screens call it «пауза между выступлениями».
_Avoid_: Interlude (that is a block-less entry), gap, transition

**Block**:
A titled section of the schedule: a block start and every event after it up to the next block start. An event's block is wherever it sits, so moving it across a block start moves it into that block.
_Avoid_: Section, group

## Notifications

**Notification**:
One message for one user, shown in their in-app feed and delivered to each channel they can be reached on.
_Avoid_: Message, alert

**Mailing**:
One send of a notification to many users at once, which is tracked, counted and can be cancelled as a whole. The English name is a calque of «рассылка», the word the organizers' screens use.
_Avoid_: Campaign, batch, dispatch, mail (it is never email)

**Broadcast**:
A mailing an organizer writes by hand for every user holding the chosen roles. The other kind is a change announcement, so "broadcast" never names a mailing in general.
_Avoid_: Announcement

**Change announcement**:
A mailing a schedule change sends on its own to the users subscribed to the events it touches. The screens call it «уведомление об изменении».
_Avoid_: Schedule fan-out, change notification

**Reminder**:
The one notice a subscription sends before its act: once the act is estimated to be within the subscriber's lead time, or two positions from the stage, whichever comes first. The estimate sums the planned durations of the acts ahead, so it is always "примерно". The screens call it «напоминание».
_Avoid_: Countdown, alert

**Channel**:
A route a notification reaches a user by outside the app: Telegram, VK or Web Push.
_Avoid_: Provider, transport

## Quest

**Quest**:
A festival-wide game: players do tasks around the venue, volunteers give them points, and the top of the leaderboard wins merch. Organizers switch it on for a festival. The screens call it «квест».
_Avoid_: Game, challenge, gamification (in copy)

**Player**:
Any user taking part in the quest; staff included, though nobody can give points to themselves. The screens call one «игрок».
_Avoid_: Participant (that is a performer)

**Award**:
One grant of points to a player by a volunteer, with a note saying what for. An award can be cancelled but never edited or deleted. The screens call one «начисление».
_Avoid_: Transaction, transfer, reward

**Points**:
A player's balance: the sum of their awards that are not cancelled. Points are only earned, never spent. The screens call them «баллы».
_Avoid_: Coins, score, credits

**Leaderboard**:
Players ranked by points, ties going to whoever reached the score first, so no two players share a place. The screens call it «таблица лидеров».
_Avoid_: Rating, top
