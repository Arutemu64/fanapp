from __future__ import annotations

from secrets import randbelow

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.core.vo.user import Username

RUSSIAN_ADJECTIVES: tuple[str, ...] = (
    "Алый",
    "Волшебный",
    "Восточный",
    "Звёздный",
    "Золотой",
    "Изящный",
    "Лазурный",
    "Легендарный",
    "Лесной",
    "Лунный",
    "Нежный",
    "Радужный",
    "Светлый",
    "Северный",
    "Сказочный",
    "Снежный",
    "Солнечный",
    "Тайный",
    "Тёплый",
    "Утренний",
    "Хрустальный",
    "Чудесный",
    "Ясный",
    "Яшмовый",
)

RUSSIAN_NOUNS: tuple[str, ...] = (
    "Авантюрист",
    "Алхимик",
    "Бард",
    "Вестник",
    "Волшебник",
    "Грифон",
    "Дракон",
    "Жрец",
    "Искатель",
    "Капитан",
    "Кицунэ",
    "Лис",
    "Лучник",
    "Маг",
    "Мастер",
    "Навигатор",
    "Паладин",
    "Рыцарь",
    "Сапфир",
    "Скиталец",
    "Странник",
    "Феникс",
    "Хранитель",
    "Чародей",
)


class UserService:
    def __init__(self, user_gateway: UserGateway) -> None:
        self.user_gateway = user_gateway

    async def generate_username(self) -> Username:
        for _ in range(500):
            candidate = self._build_candidate()
            if not await self.user_gateway.get_user_by_username(candidate):
                return Username(candidate)

        msg = "Could not generate unique username"
        raise RuntimeError(msg)

    @staticmethod
    def _build_candidate() -> str:
        adjective = RUSSIAN_ADJECTIVES[randbelow(len(RUSSIAN_ADJECTIVES))]
        noun = RUSSIAN_NOUNS[randbelow(len(RUSSIAN_NOUNS))]
        suffix = f"{randbelow(100):02d}"
        return f"{adjective}{noun}{suffix}"
