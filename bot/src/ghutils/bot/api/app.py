import os

import uvicorn
from fastapi import FastAPI

from ghutils.bot.db.engine import SessionDependency, check_db_connection

app = FastAPI()


@app.get("/login")
def get_login(code: str, state: str, session: SessionDependency):
    print(f"{code=}, {state=}")


if __name__ == "__main__":
    check_db_connection()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
