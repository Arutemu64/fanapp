from dishka import Provider, Scope, provide

from fanfan.adapters.profanity.filter import WordListProfanityFilter
from fanfan.application.ports.profanity_filter import ProfanityFilter


class ProfanityProvider(Provider):
    scope = Scope.APP

    @provide
    def get_profanity_filter(self) -> ProfanityFilter:
        return WordListProfanityFilter()
