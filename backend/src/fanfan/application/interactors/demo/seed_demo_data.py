import logging
from dataclasses import dataclass, replace

from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.gateways.schedule_events import ScheduleEventGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.vo.nomination import NominationCode, generate_nomination_id
from fanfan.core.vo.participant import generate_participant_id
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_event import generate_schedule_event_id

logger = logging.getLogger(__name__)

# Demo rows carry cosplay2_id values in a high, reserved band so the voting seed
# upserts its own records by natural key on every run and never collides with a
# real Cosplay2 sync (the vendor's ids are far smaller). Nominations occupy the
# base band; participants the +1000 band, both offset by list position.
_DEMO_NOMINATION_ID_BASE = 900_000
_DEMO_PARTICIPANT_ID_BASE = 901_000

# Matches ImportSchedule: events start at 100 and step by 100 so an organizer can
# later drop rows between them without renumbering (order is a float column).
_ORDER_INIT = 100.0
_ORDER_STEP = 100.0


@dataclass(frozen=True, slots=True)
class _DemoParticipant:
    title: str
    voting_number: int


@dataclass(frozen=True, slots=True)
class _DemoNomination:
    code: str
    title: str
    participants: tuple[_DemoParticipant, ...]


@dataclass(frozen=True, slots=True)
class _DemoEvent:
    number: int
    title: str
    # Planned stage time in seconds, the unit ScheduleEvent.duration expects.
    duration: int
    block_title: str
    nomination_title: str | None


# Three votable nominations with a handful of entries each — enough to exercise
# the voting UI (list, single-nomination view, casting and cancelling a vote).
DEMO_NOMINATIONS: tuple[_DemoNomination, ...] = (
    _DemoNomination(
        code="demo-solo",
        title="Одиночное дефиле",
        participants=(
            _DemoParticipant(title="Хацунэ Мику — Vocaloid", voting_number=1),
            _DemoParticipant(title="Эдвард Элрик — Стальной алхимик", voting_number=2),
            _DemoParticipant(title="Сейлор Мун — Сейлор Мун", voting_number=3),
            _DemoParticipant(
                title="Тандзиро Камадо — Клинок, рассекающий демонов",
                voting_number=4,
            ),
        ),
    ),
    _DemoNomination(
        code="demo-group",
        title="Групповое дефиле",
        participants=(
            _DemoParticipant(title="Команда 7 — Наруто", voting_number=1),
            _DemoParticipant(title="Отряд разведки — Атака титанов", voting_number=2),
            _DemoParticipant(
                title="Класс 1-А — Моя геройская академия", voting_number=3
            ),
        ),
    ),
    _DemoNomination(
        code="demo-karaoke",
        title="Караоке",
        participants=(
            _DemoParticipant(
                title="«A Cruel Angel's Thesis» — Евангелион", voting_number=1
            ),
            _DemoParticipant(
                title="«Gurenge» — Клинок, рассекающий демонов", voting_number=2
            ),
            _DemoParticipant(title="«Unravel» — Токийский гуль", voting_number=3),
        ),
    ),
)

# A short festival day: an opening, the two defile blocks whose entries mirror
# the votable nominations above, a concert block and a closing ceremony.
DEMO_SCHEDULE: tuple[_DemoEvent, ...] = (
    _DemoEvent(
        number=1,
        title="Торжественное открытие фестиваля",
        duration=900,
        block_title="Открытие",
        nomination_title=None,
    ),
    _DemoEvent(
        number=2,
        title="Хацунэ Мику — Vocaloid",
        duration=180,
        block_title="Одиночное дефиле",
        nomination_title="Одиночное дефиле",
    ),
    _DemoEvent(
        number=3,
        title="Эдвард Элрик — Стальной алхимик",
        duration=180,
        block_title="Одиночное дефиле",
        nomination_title="Одиночное дефиле",
    ),
    _DemoEvent(
        number=4,
        title="Сейлор Мун — Сейлор Мун",
        duration=180,
        block_title="Одиночное дефиле",
        nomination_title="Одиночное дефиле",
    ),
    _DemoEvent(
        number=5,
        title="Тандзиро Камадо — Клинок, рассекающий демонов",
        duration=180,
        block_title="Одиночное дефиле",
        nomination_title="Одиночное дефиле",
    ),
    _DemoEvent(
        number=6,
        title="Перерыв",
        duration=600,
        block_title="Перерыв",
        nomination_title=None,
    ),
    _DemoEvent(
        number=7,
        title="Команда 7 — Наруто",
        duration=300,
        block_title="Групповое дефиле",
        nomination_title="Групповое дефиле",
    ),
    _DemoEvent(
        number=8,
        title="Отряд разведки — Атака титанов",
        duration=300,
        block_title="Групповое дефиле",
        nomination_title="Групповое дефиле",
    ),
    _DemoEvent(
        number=9,
        title="Класс 1-А — Моя геройская академия",
        duration=300,
        block_title="Групповое дефиле",
        nomination_title="Групповое дефиле",
    ),
    _DemoEvent(
        number=10,
        title="Караоке-баттл",
        duration=1200,
        block_title="Концертная программа",
        nomination_title="Караоке",
    ),
    _DemoEvent(
        number=11,
        title="Награждение и закрытие",
        duration=1200,
        block_title="Закрытие",
        nomination_title=None,
    ),
)


class SeedDemoData:
    """Populate an environment with a demo programme and voting.

    A development/demo convenience: it fills the schedule and voting so both
    features can be shown end-to-end without a real Cosplay2 sync or a
    spreadsheet import. Idempotent — safe to run more than once.
    """

    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        nomination_gateway: NominationGateway,
        participant_gateway: ParticipantGateway,
        settings_gateway: AppSettingsGateway,
        uow: UnitOfWork,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ):
        self.schedule_gateway = schedule_gateway
        self.nomination_gateway = nomination_gateway
        self.participant_gateway = participant_gateway
        self.settings_gateway = settings_gateway
        self.uow = uow
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def _seed_schedule(self) -> None:
        # The schedule has no natural key per row and its `order` column is
        # unique, so re-seeding onto an existing programme would either collide
        # on order or clobber an organizer's real events. Only seed a blank one;
        # leave any existing programme untouched.
        if await self.schedule_gateway.list_all():
            logger.info("Schedule already has events, skipping demo programme")
            return
        order = _ORDER_INIT
        for entry in DEMO_SCHEDULE:
            event = ScheduleEvent(
                id=generate_schedule_event_id(),
                number=entry.number,
                title=entry.title,
                duration=entry.duration,
                block_title=entry.block_title,
                nomination_title=entry.nomination_title,
                order=order,
                is_current=False,
                is_skipped=False,
            )
            await self.schedule_gateway.add(event)
            order += _ORDER_STEP
        logger.info("Demo programme seeded", extra={"events": len(DEMO_SCHEDULE)})

    async def _seed_voting(self) -> None:
        # Upsert by the reserved cosplay2_id so a re-run refreshes the demo rows
        # in place instead of duplicating them, exactly as SyncCosplay does for
        # real vendor records.
        for nomination_index, demo_nomination in enumerate(DEMO_NOMINATIONS):
            cosplay2_id = _DEMO_NOMINATION_ID_BASE + nomination_index
            nomination = await self.nomination_gateway.get_by_cosplay2_id(cosplay2_id)
            if nomination:
                nomination = replace(
                    nomination,
                    code=NominationCode(demo_nomination.code),
                    title=demo_nomination.title,
                    is_votable=True,
                )
                await self.nomination_gateway.save(nomination)
            else:
                nomination = Nomination(
                    id=generate_nomination_id(),
                    cosplay2_id=cosplay2_id,
                    code=NominationCode(demo_nomination.code),
                    title=demo_nomination.title,
                    is_votable=True,
                )
                await self.nomination_gateway.add(nomination)
            await self._seed_participants(nomination, demo_nomination, nomination_index)
        logger.info("Demo voting seeded", extra={"nominations": len(DEMO_NOMINATIONS)})

    async def _seed_participants(
        self,
        nomination: Nomination,
        demo_nomination: _DemoNomination,
        nomination_index: int,
    ) -> None:
        for participant_index, demo_participant in enumerate(
            demo_nomination.participants
        ):
            # Stable within a nomination: index the band by nomination so two
            # nominations' participants never share a reserved cosplay2_id.
            cosplay2_id = (
                _DEMO_PARTICIPANT_ID_BASE + nomination_index * 100 + participant_index
            )
            participant = await self.participant_gateway.get_by_cosplay2_id(cosplay2_id)
            if participant:
                participant = replace(
                    participant,
                    title=demo_participant.title,
                    nomination_id=nomination.id,
                    voting_number=demo_participant.voting_number,
                )
                await self.participant_gateway.save(participant)
            else:
                participant = Participant(
                    id=generate_participant_id(),
                    cosplay2_id=cosplay2_id,
                    title=demo_participant.title,
                    nomination_id=nomination.id,
                    voting_number=demo_participant.voting_number,
                )
                await self.participant_gateway.add(participant)

    async def _enable_voting(self) -> None:
        # Voting entries are invisible until the global flag is on, so flip it —
        # the whole point of the seed is a voting flow that works out of the box.
        settings = await self.settings_gateway.get_for_update()
        settings.set_voting_enabled(enabled=True)
        await self.settings_gateway.save(settings)

    async def __call__(self) -> None:
        # Runs as the seeded system user under the CLI, granted demo:seed by
        # migration — the check is real, like every other unattended interactor.
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.DEMO_SEED
        )

        await self._seed_schedule()
        await self._seed_voting()
        await self._enable_voting()

        await self.uow.commit()
        logger.info("Demo data seeded", extra={"actor_id": str(current_user.id)})
