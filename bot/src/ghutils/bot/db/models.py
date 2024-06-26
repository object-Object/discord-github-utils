from sqlmodel import Field, SQLModel  # pyright: ignore[reportUnknownVariableType]

from .engine import engine


class UserGitHubToken(SQLModel, table=True):
    user_id: str = Field(primary_key=True)
    access_token: str = Field(repr=False)
    refresh_token: str = Field(repr=False)


class UserLogin(SQLModel, table=True):
    user_id: str = Field(primary_key=True)
    uuid: str


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
