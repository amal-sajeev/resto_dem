"""
Create all tables in the database. Run from project root:
  python -m scripts.init_db
Requires .env with DATABASE_URL (postgresql+asyncpg://...).
"""
import asyncio
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import engine
from app.models import Base


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")


async def main() -> None:
    await create_tables()


if __name__ == "__main__":
    asyncio.run(main())
