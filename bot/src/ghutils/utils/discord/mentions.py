from datetime import datetime


def relative_timestamp(when: datetime):
    return f"<t:{when.timestamp():.0f}:R>"
