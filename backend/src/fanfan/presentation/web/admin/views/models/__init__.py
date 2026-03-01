from .nomination import NominationView
from .participant import ParticipantView
from .schedule_event import ScheduleEventView
from .ticket import TicketView
from .user import UserView
from .vote import VoteView

model_views = [
    ScheduleEventView,
    NominationView,
    ParticipantView,
    TicketView,
    UserView,
    VoteView,
]
