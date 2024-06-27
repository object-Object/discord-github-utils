from sqlalchemy import BigInteger, Engine
from sqlmodel import Field, SQLModel  # pyright: ignore[reportUnknownVariableType]


class UserGitHubTokens(SQLModel, table=True):
    user_id: int = Field(primary_key=True, sa_type=BigInteger)
    access_token: str = Field(repr=False)
    refresh_token: str = Field(repr=False)


class UserLogin(SQLModel, table=True):
    user_id: int = Field(primary_key=True, sa_type=BigInteger)
    login_id: str


def create_db_and_tables(engine: Engine):
    SQLModel.metadata.create_all(engine)
