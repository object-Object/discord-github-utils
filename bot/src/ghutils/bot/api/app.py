import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import Engine
from sqlmodel import Session, create_engine

from ghutils.bot.core.env import GHUtilsEnv
from ghutils.bot.db.engine import check_db_connection
from ghutils.bot.db.models import UserLogin

logger = logging.getLogger(__name__)

engine: Engine


def get_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = create_engine(GHUtilsEnv.get().db_url)
    check_db_connection(engine)
    yield


app = FastAPI(
    lifespan=lifespan,
)


@app.get("/login")
def get_login(
    code: str,
    state: str,
    session: Annotated[Session, Depends(get_session)],
):
    print(f"{code=}, {state=}")

    try:
        login = UserLogin.model_validate_json(state)
    except (ValueError, ValidationError) as e:
        logger.debug(f"Failed to parse login state: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to parse login state")

    match db_login := session.get(UserLogin, login.user_id):
        case UserLogin(login_id=login.login_id):
            session.delete(db_login)
        case UserLogin() | None:
            logger.debug(f"Invalid login state: {db_login}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid login state")

    session.commit()


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
