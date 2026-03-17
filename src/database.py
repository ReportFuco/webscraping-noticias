# database.py
from sqlmodel import SQLModel, create_engine, Session
from config import *


DATABASE_URL =f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@localhost:5432/{DATABASE_NAME}"

engine = create_engine(DATABASE_URL, echo=False)


def create_db():
    """Crea todas las tablas si no existen"""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session