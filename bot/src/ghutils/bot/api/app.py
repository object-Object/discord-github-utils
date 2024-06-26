import os

import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get("/login")
def get_login(code: str, state: str):
    print(f"{code=}, {state=}")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
