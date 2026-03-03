"""
One-command server setup: reset database (drop + create tables), seed restaurants/rooms/menus, then seed orders.
Run from project root: python -m scripts.setup

Requires .env with DATABASE_URL (postgresql+asyncpg://...).
"""
import asyncio
import importlib.util
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


async def reset_db() -> None:
    """Drop all tables and recreate them."""
    from app.database import engine
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database reset: tables dropped and recreated.")


async def run_seed() -> None:
    """Load and run the seed script in this process."""
    seed_path = Path(__file__).parent / "seed.py"
    spec = importlib.util.spec_from_file_location("seed", seed_path)
    assert spec and spec.loader, "Could not load seed module"
    seed_mod = importlib.util.module_from_spec(spec)
    sys.modules["seed"] = seed_mod
    spec.loader.exec_module(seed_mod)
    await seed_mod.seed()


async def run_seed_orders() -> None:
    """Load and run the seed_orders script in this process."""
    seed_orders_path = Path(__file__).parent / "seed_orders.py"
    spec = importlib.util.spec_from_file_location("seed_orders", seed_orders_path)
    assert spec and spec.loader, "Could not load seed_orders module"
    seed_orders_mod = importlib.util.module_from_spec(spec)
    sys.modules["seed_orders"] = seed_orders_mod
    spec.loader.exec_module(seed_orders_mod)
    await seed_orders_mod.seed_orders(clear=True)


async def main() -> None:
    print("Setting up database...")
    await reset_db()
    print("Seeding data...")
    await run_seed()
    print("Seeding orders...")
    await run_seed_orders()
    print("Setup complete. Start the app with: uvicorn app.main:app --host 0.0.0.0")


if __name__ == "__main__":
    asyncio.run(main())
