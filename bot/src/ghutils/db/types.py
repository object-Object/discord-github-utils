from datetime import datetime, timezone

from sqlalchemy import Dialect
from sqlalchemy.types import DateTime, String, TypeDecorator

from ghutils.utils.github import Repository


class RepositoryType(TypeDecorator[Repository]):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Repository | None, dialect: Dialect):
        if value is not None:
            return str(value)

    def process_result_value(self, value: str | None, dialect: Dialect):
        if value is not None:
            return Repository.parse(value)


# https://docs.sqlalchemy.org/en/20/core/custom_types.html#store-timezone-aware-timestamps-as-timezone-naive-utc
class DatetimeType(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect):
        if value is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect):
        if value is not None:
            return value.replace(tzinfo=timezone.utc)
