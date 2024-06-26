from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlmodel import Session

from ghutils.bot.core.env import GHUtilsEnv

engine = create_engine(GHUtilsEnv.get().db_url)


def check_db_connection():
    with Session(engine) as session:
        session.connection()


def get_session():
    with Session(engine) as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]
