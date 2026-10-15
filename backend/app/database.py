from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


# Use aiosqlite for local dev if no postgres configured
db_url = settings.database_url
if "sqlite" in db_url and "aiosqlite" not in db_url:
    db_url = db_url.replace("sqlite:", "sqlite+aiosqlite:")

engine = create_async_engine(db_url, echo=settings.app_debug)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables. Used for dev/testing. Production should use Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
