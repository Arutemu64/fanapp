# FAN FAN companion app

Companion web app for the FAN FAN anime convention: visitors follow the programme, vote and get notified; organizers run the programme and message visitors.

## Roles

**Role**:
What a user is at the festival. Every user holds exactly one; broadcasts are addressed by role, and a ticket carries the role its holder gets. Beyond the organizer role opening the organizer tools, a role lets a user do nothing by itself.
_Avoid_: Group, user type

**Permission**:
One organizer power, such as managing the programme or sending broadcasts, granted to a user one by one and independent of their role.
_Avoid_: Right, access, role

**Visitor**:
A user who came to watch, the role every new account starts with. The screens call one «зритель».
_Avoid_: Guest («гость» at a convention means an invited star), attendee

**Participant**:
Someone who performs at the festival. The same person holds the participant role and is a voting entry in a nomination. The screens call one «участник».
_Avoid_: Performer, contestant, cosplayer

**Volunteer**:
A user who helps run the festival on site. The screens call one «волонтёр».
_Avoid_: Helper, staff

**Organizer**:
A user who runs the festival. The screens call one «организатор».
_Avoid_: Org, organiser, admin

## Programme

**Entry**:
One row of the programme, in order: an event or a block start.
_Avoid_: Row, item

**Event**:
An entry for something on stage — an act, a break, the opening. Only events are numbered, timed, given a position, made current, skipped, moved or subscribed to. The screens call one «выступление».
_Avoid_: Performance, act (in code)

**Position**:
An event's place in the running order, 1..N, counting only events that are not skipped. "Осталось N выступлений" and subscription reminders count positions.
_Avoid_: Queue

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
