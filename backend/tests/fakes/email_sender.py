from fanfan.application.ports.email_sender import EmailMessage, EmailSender


class FakeEmailSender(EmailSender):
    """Records sent emails instead of talking to an SMTP server.

    Tests assert on ``sent_messages`` to check what would have been emailed.
    """

    def __init__(self) -> None:
        self.sent_messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent_messages.append(message)
