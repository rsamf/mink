from typing import Generator
from sqlmodel import SQLModel, create_engine, Session
from omegaconf import DictConfig
import logging


logger = logging.getLogger(__name__)
engine = None


def get_db_url(cfg: DictConfig) -> str:
    db_cfg = cfg.get("db")
    if db_cfg is None:
        return "sqlite:///./test.db"

    assert db_cfg.provider == "cloudsql", "Only cloudsql is supported for now"

    user = db_cfg.user
    password = db_cfg.password
    host = db_cfg.host
    port = db_cfg.port
    name = db_cfg.name

    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def init_db(cfg: DictConfig):
    global engine

    url = get_db_url(cfg)
    logger.info(f"Connecting to database at {url}")
    engine = create_engine(url)
    logger.info("Creating tables in database")
    SQLModel.metadata.create_all(engine)
    logger.info(f"Database initialized at {url}")


def get_session() -> Generator[Session, None, None]:
    if engine is None:
        raise RuntimeError("Database engine not initialized")
    with Session(engine) as session:
        yield session
