from secrets import randbelow

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.core.vo.user import Username

# Kept masculine-only so adjective + noun agreement holds for every pair
# (the words are concatenated, e.g. "ПушистыйКотик07"). Leans friendly and
# generic over RPG jargon — the audience is casual con-goers, not gamers.
RUSSIAN_ADJECTIVES: tuple[str, ...] = (
    "Алый",
    "Весёлый",
    "Волшебный",
    "Восточный",
    "Дерзкий",
    "Звёздный",
    "Золотой",
    "Изящный",
    "Космический",
    "Лазурный",
    "Легендарный",
    "Лесной",
    "Лунный",
    "Нежный",
    "Неоновый",
    "Огненный",
    "Пушистый",
    "Радужный",
    "Светлый",
    "Северный",
    "Сказочный",
    "Смелый",
    "Снежный",
    "Солнечный",
    "Тайный",
    "Тёплый",
    "Утренний",
    "Хрустальный",
    "Чудесный",
    "Шустрый",
    "Ясный",
    "Яшмовый",
)

RUSSIAN_NOUNS: tuple[str, ...] = (
    "Авантюрист",
    "Волшебник",
    "Грифон",
    "Гром",
    "Дельфин",
    "Дракон",
    "Единорог",
    "Ёжик",
    "Искатель",
    "Капитан",
    "Космонавт",
    "Котик",
    "Лев",
    "Лис",
    "Маг",
    "Мастер",
    "Метеор",
    "Навигатор",
    "Пилот",
    "Пингвин",
    "Пончик",
    "Робот",
    "Рыцарь",
    "Сапфир",
    "Странник",
    "Тигр",
    "Феникс",
    "Хранитель",
    "Чемпион",
)


class UserService:
    def __init__(self, user_gateway: UserGateway) -> None:
        self.user_gateway = user_gateway

    async def generate_username(self) -> Username:
        for _ in range(500):
            candidate = self._build_candidate()
            if not await self.user_gateway.get_by_username(candidate):
                return Username(candidate)

        msg = "Could not generate unique username"
        raise RuntimeError(msg)

    @staticmethod
    def _build_candidate() -> str:
        adjective = RUSSIAN_ADJECTIVES[randbelow(len(RUSSIAN_ADJECTIVES))]
        noun = RUSSIAN_NOUNS[randbelow(len(RUSSIAN_NOUNS))]
        suffix = f"{randbelow(100):02d}"
        return f"{adjective}{noun}{suffix}"
