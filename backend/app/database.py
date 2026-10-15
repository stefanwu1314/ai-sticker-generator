import os
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data.db')

# SQLite connections may be reused across FastAPI threadpool threads.
connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    return Session(engine)
