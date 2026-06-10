from dishka import Provider, Scope, provide

from fanfan.adapters.html.sanitizer import Nh3HtmlSanitizer
from fanfan.application.ports.html_sanitizer import HtmlSanitizer


class HtmlProvider(Provider):
    scope = Scope.APP

    @provide
    def get_html_sanitizer(self) -> HtmlSanitizer:
        return Nh3HtmlSanitizer()
