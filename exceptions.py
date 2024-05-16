class InvalidResponseCode(Exception):
    """Не верный код ответа."""

    pass


class HomeworkVerdictNotFound(ValueError):
    """Не верный статус домашней работы."""

    pass
