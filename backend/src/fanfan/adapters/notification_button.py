"""The label of the link button the messenger notifiers attach.

Telegram and VK both show one button that opens ``notification.path``; naming
it after the destination tells the reader where it leads before they tap.
"""

_DEFAULT_LABEL = "🌐 Открыть приложение"

# Keep labels within VK's 40-character button limit.
_LABELS_BY_PATH: dict[str, str] = {
    "/schedule": "📅 Открыть программу",
    "/schedule/changes": "📅 Изменения в программе",
    "/notifications": "🔔 Все уведомления",
    "/profile/notifications": "⚙️ Настройки уведомлений",
}


def button_label_for(path: str | None) -> str:
    if path is None:
        return _DEFAULT_LABEL
    return _LABELS_BY_PATH.get(path, _DEFAULT_LABEL)
