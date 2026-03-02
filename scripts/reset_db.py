"""
Drop all tables and recreate them. Use when schema changed (e.g. UUID vs integer).
Run: python -m scripts.reset_db
Then: python -m scripts.seed
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import engine
from app.models import Base


async def reset() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Tables dropped and recreated. Run: python -m scripts.seed")


if __name__ == "__main__":
    asyncio.run(reset())
