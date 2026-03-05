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


async def create_tables(drop_existing: bool = False) -> None:
    async with engine.begin() as conn:
        if drop_existing:
            await conn.run_sync(Base.metadata.drop_all)
            print("Existing tables dropped.")
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")


async def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true", help="Drop all existing tables first")
    args = parser.parse_args()
    await create_tables(drop_existing=args.drop)


if __name__ == "__main__":
    asyncio.run(main())
