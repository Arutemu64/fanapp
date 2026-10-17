from secrets import randbelow

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.core.vo.user import Username

# Each name keeps one grammatical gender throughout, so the adjective agrees
# with its noun (the words are concatenated, e.g. "ЛунныйЛис07", "ЛуннаяЛиса07").
# The gender belongs to the words, not the user: the app never asks for one, and
# the profile's reroll button lets anyone swap a name they don't like. The tone
# is playful and lightly themed (night, fantasy, samurai, anime food) without
# fandom slang like "кун", "тян" or "отаку" — the audience is casual con-goers.
# Words stay short so the trailing digits, which tell two namesakes apart,
# survive the narrow rows on a phone. No "ё": phones hide it behind a
# long-press and lower() does not fold it to "е", so a volunteer typing the name
# into the quest player search would never find the player.
# Left out on purpose: slang double meanings ("Синий" = drunk, "Голубой",
# "Кекс", "Выдра", "Креветка", "Вафля", "Белка", "Ночная фея"), "Радужный",
# which reads as an LGBT symbol in Russia, and nouns that repeat an adjective's
# root ("Луна", "Мята").
# (masculine, feminine) forms of each adjective.
RUSSIAN_ADJECTIVES: tuple[tuple[str, str], ...] = (
    ("Алый", "Алая"),
    ("Бодрый", "Бодрая"),
    ("Бойкий", "Бойкая"),
    ("Бравый", "Бравая"),
    ("Важный", "Важная"),
    ("Гордый", "Гордая"),
    ("Дерзкий", "Дерзкая"),
    ("Добрый", "Добрая"),
    ("Дикий", "Дикая"),
    ("Звонкий", "Звонкая"),
    ("Золотой", "Золотая"),
    ("Лазурный", "Лазурная"),
    ("Ледяной", "Ледяная"),
    ("Лесной", "Лесная"),
    ("Лиловый", "Лиловая"),
    ("Лихой", "Лихая"),
    ("Ловкий", "Ловкая"),
    ("Лунный", "Лунная"),
    ("Медный", "Медная"),
    ("Милый", "Милая"),
    ("Морской", "Морская"),
    ("Мудрый", "Мудрая"),
    ("Мятный", "Мятная"),
    ("Небесный", "Небесная"),
    ("Неоновый", "Неоновая"),
    ("Ночной", "Ночная"),
    ("Огненный", "Огненная"),
    ("Пушистый", "Пушистая"),
    ("Резвый", "Резвая"),
    ("Рыжий", "Рыжая"),
    ("Смелый", "Смелая"),
    ("Снежный", "Снежная"),
    ("Сонный", "Сонная"),
    ("Тайный", "Тайная"),
    ("Тихий", "Тихая"),
    ("Хитрый", "Хитрая"),
    ("Шустрый", "Шустрая"),
    ("Юркий", "Юркая"),
    ("Яркий", "Яркая"),
    ("Ясный", "Ясная"),
)

MASCULINE_NOUNS: tuple[str, ...] = (
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

FEMININE_NOUNS: tuple[str, ...] = (
    "Акула",
    "Буря",
    "Ведунья",
    "Виверна",
    "Вишня",
    "Волна",
    "Волчица",
    "Вспышка",
    "Вьюга",
    "Героиня",
    "Гроза",
    "Дриада",
    "Звезда",
    "Ириска",
    "Искра",
    "Касатка",
    "Катана",
    "Кобра",
    "Комета",
    "Кошка",
    "Лань",
    "Лиса",
    "Лучница",
    "Медуза",
    "Метель",
    "Молния",
    "Панда",
    "Пантера",
    "Пастила",
    "Пчела",
    "Ракета",
    "Русалка",
    "Рысь",
    "Сакура",
    "Сирена",
    "Сова",
    "Сойка",
    "Тень",
    "Химера",
    "Чайка",
)


class UserService:
    def __init__(self, user_gateway: UserGateway) -> None:
        self.user_gateway = user_gateway

    async def generate_username(self) -> Username:
        for _ in range(500):
            masculine, feminine = RUSSIAN_ADJECTIVES[randbelow(len(RUSSIAN_ADJECTIVES))]
            if randbelow(2):
                adjective, nouns = feminine, FEMININE_NOUNS
            else:
                adjective, nouns = masculine, MASCULINE_NOUNS
            noun = nouns[randbelow(len(nouns))]
            candidate = f"{adjective}{noun}{randbelow(100):02d}"
            if not await self.user_gateway.get_by_username(candidate):
                return Username(candidate)

        msg = "Could not generate unique username"
        raise RuntimeError(msg)
