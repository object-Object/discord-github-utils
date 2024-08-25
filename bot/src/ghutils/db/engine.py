from sqlalchemy import Engine
from sqlmodel import Session


def check_db_connection(engine: Engine):
    with Session(engine) as session:
        session.connection()
