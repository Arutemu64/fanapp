from fanfan.application.ports.sources.cosplay import (
    CosplaySource,
    ExternalNomination,
    ExternalParticipant,
)


class FakeCosplaySource(CosplaySource):
    """In-memory CosplaySource replacing the Cosplay2 HTTP client in tests.

    A test assigns what the vendor should report (``nominations`` /
    ``participants``). Set ``raises`` to make a fetch blow up, which is how the
    failure path of the sync interactors is exercised.
    """

    def __init__(self) -> None:
        self.nominations: list[ExternalNomination] = []
        self.participants: list[ExternalParticipant] = []
        self.raises: Exception | None = None

    async def fetch_nominations(self) -> list[ExternalNomination]:
        if self.raises is not None:
            raise self.raises
        return self.nominations

    async def fetch_participants(self) -> list[ExternalParticipant]:
        if self.raises is not None:
            raise self.raises
        return self.participants
