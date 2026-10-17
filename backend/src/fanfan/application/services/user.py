from secrets import randbelow

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.core.vo.user import Username

# Kept masculine-only so adjective + noun agreement holds for every pair
# (the words are concatenated, e.g. "ЛунныйЛис07"). The tone is playful and
# lightly themed (night, fantasy, samurai, anime food) without fandom slang
# like "кун", "тян" or "отаку" — the audience is casual con-goers. Words stay
# short so the trailing digits, which tell two namesakes apart, survive the
# truncated rows on a phone. No "ё": phones hide it behind a long-press and
# lower() does not fold it to "е", so a volunteer typing the name into the
# quest player search would never find the player.
# Left out on purpose: slang double meanings ("Синий" = drunk, "Голубой",
# "Кекс") and "Радужный", which reads as an LGBT symbol in Russia.
RUSSIAN_ADJECTIVES: tuple[str, ...] = (
    "Алый",
    "Бодрый",
    "Бойкий",
    "Бравый",
    "Важный",
    "Гордый",
    "Дерзкий",
    "Добрый",
    "Дикий",
    "Звонкий",
    "Золотой",
    "Лазурный",
    "Ледяной",
    "Лесной",
    "Лиловый",
    "Лихой",
    "Ловкий",
    "Лунный",
    "Медный",
    "Милый",
    "Морской",
    "Мудрый",
    "Мятный",
    "Небесный",
    "Неоновый",
    "Ночной",
    "Огненный",
    "Пушистый",
    "Резвый",
    "Рыжий",
    "Смелый",
    "Снежный",
    "Сонный",
    "Тайный",
    "Тихий",
    "Хитрый",
    "Шустрый",
    "Юркий",
    "Яркий",
    "Ясный",
)

RUSSIAN_NOUNS: tuple[str, ...] = (
    "Барсук",
    "Ворон",
    "Вихрь",
    "Волк",
    "Герой",
    "Гром",
    "Грифон",
    "Дракон",
    "Енот",
    "Капитан",
    "Кит",
    "Кот",
    "Кракен",
    "Леденец",
    "Лис",
    "Маг",
    "Мечник",
    "Метеор",
    "Ниндзя",
    "Пиксель",
    "Пилот",
    "Пингвин",
    "Пончик",
    "Призрак",
    "Пудинг",
    "Рамен",
    "Ронин",
    "Рыцарь",
    "Самурай",
    "Сокол",
    "Страж",
    "Сурок",
    "Сыщик",
    "Тайфун",
    "Тануки",
    "Тигр",
    "Феникс",
    "Филин",
    "Хомяк",
    "Шторм",
)


class UserService:
    def __init__(self, user_gateway: UserGateway) -> None:
        self.user_gateway = user_gateway

    async def generate_username(self) -> Username:
        for _ in range(500):
            adjective = RUSSIAN_ADJECTIVES[randbelow(len(RUSSIAN_ADJECTIVES))]
            noun = RUSSIAN_NOUNS[randbelow(len(RUSSIAN_NOUNS))]
            candidate = f"{adjective}{noun}{randbelow(100):02d}"
            if not await self.user_gateway.get_by_username(candidate):
                return Username(candidate)

        msg = "Could not generate unique username"
        raise RuntimeError(msg)
