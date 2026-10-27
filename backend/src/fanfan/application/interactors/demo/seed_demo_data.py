import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from fanfan.application.interactors.schedule_mgmt.import_schedule import (
    ORDER_INIT,
    ORDER_STEP,
    ScheduleBlockRow,
    ScheduleEventRow,
    ScheduleRow,
    build_schedule_entry,
)
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.gateways.schedule_entries import ScheduleEntryGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant
from fanfan.core.vo.nomination import NominationCode, generate_nomination_id
from fanfan.core.vo.participant import generate_participant_id
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)

_DEMO_NOMINATION_ID_BASE = 900_000
_DEMO_PARTICIPANT_ID_BASE = 901_000


@dataclass(frozen=True, slots=True)
class _DemoParticipant:
    title: str
    voting_number: int


@dataclass(frozen=True, slots=True)
class _DemoNomination:
    code: str
    title: str
    participants: tuple[_DemoParticipant, ...]


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

DEMO_SCHEDULE: tuple[ScheduleRow, ...] = (
    ScheduleBlockRow(title="Открытие"),
    ScheduleEventRow(
        number=1,
        title="Торжественное открытие фестиваля",
        duration=900,
        nomination_title=None,
    ),
    ScheduleBlockRow(title="Одиночное дефиле"),
    ScheduleEventRow(
        number=2,
        title="Хацунэ Мику — Vocaloid",
        duration=180,
        nomination_title="Одиночное дефиле",
    ),
    ScheduleEventRow(
        number=3,
        title="Эдвард Элрик — Стальной алхимик",
        duration=180,
        nomination_title="Одиночное дефиле",
    ),
    ScheduleEventRow(
        number=4,
        title="Сейлор Мун — Сейлор Мун",
        duration=180,
        nomination_title="Одиночное дефиле",
    ),
    ScheduleEventRow(
        number=5,
        title="Тандзиро Камадо — Клинок, рассекающий демонов",
        duration=180,
        nomination_title="Одиночное дефиле",
    ),
    ScheduleBlockRow(title="Перерыв"),
    ScheduleEventRow(
        number=6,
        title="Перерыв",
        duration=600,
        nomination_title=None,
    ),
    ScheduleBlockRow(title="Групповое дефиле"),
    ScheduleEventRow(
        number=7,
        title="Команда 7 — Наруто",
        duration=300,
        nomination_title="Групповое дефиле",
    ),
    ScheduleEventRow(
        number=8,
        title="Отряд разведки — Атака титанов",
        duration=300,
        nomination_title="Групповое дефиле",
    ),
    ScheduleEventRow(
        number=9,
        title="Класс 1-А — Моя геройская академия",
        duration=300,
        nomination_title="Групповое дефиле",
    ),
    ScheduleBlockRow(title="Концертная программа"),
    ScheduleEventRow(
        number=10,
        title="Караоке-баттл",
        duration=1200,
        nomination_title="Караоке",
    ),
    ScheduleBlockRow(title="Закрытие"),
    ScheduleEventRow(
        number=11,
        title="Награждение и закрытие",
        duration=1200,
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
        schedule_gateway: ScheduleEntryGateway,
        nomination_gateway: NominationGateway,
        participant_gateway: ParticipantGateway,
        settings_gateway: AppSettingsGateway,
        uow: UnitOfWork,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.nomination_gateway = nomination_gateway
        self.participant_gateway = participant_gateway
        self.settings_gateway = settings_gateway
        self.uow = uow
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def _seed_schedule(self) -> None:
        if await self.schedule_gateway.list_all():
            logger.info("Schedule already has events, skipping demo programme")
            return
        order = ORDER_INIT
        for row in DEMO_SCHEDULE:
            await self.schedule_gateway.add(build_schedule_entry(row, order))
            order += ORDER_STEP
        logger.info("Demo programme seeded", extra={"entries": len(DEMO_SCHEDULE)})

    async def _seed_voting(self) -> None:
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
        settings = await self.settings_gateway.get_for_update()
        now = datetime.now(UTC)
        settings.set_voting_time_range(start=now, end=now + timedelta(days=1))
        await self.settings_gateway.save(settings)

    async def __call__(self) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.DEMO_SEED
        )

        await self._seed_schedule()
        await self._seed_voting()
        await self._enable_voting()

        await self.uow.commit()
        logger.info("Demo data seeded", extra={"actor_id": str(current_user.id)})
