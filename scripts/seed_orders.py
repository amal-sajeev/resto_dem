"""
Seeds realistic demo orders across all restaurants and rooms.
Run after init_db and seed:
    python -m scripts.init_db
    python -m scripts.seed
    python -m scripts.seed_orders

Pass --clear to delete all existing orders before seeding:
    python -m scripts.seed_orders --clear
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.database import async_session_maker
from app.models import (
    MenuItem,
    Order,
    OrderItem,
    OrderItemOption,
    OrderStatus,
    PaymentMethod,
    Restaurant,
    Room,
)

random.seed(42)

# ---------------------------------------------------------------------------
# Realistic note pools
# ---------------------------------------------------------------------------
ORDER_NOTES = [
    "Guest has a nut allergy",
    "Birthday celebration — please add a candle to dessert",
    "Late check-out guest, no rush",
    "VIP guest — extra attention please",
    "Children in party, need high chair",
    "Deliver to pool area, sun-bed 4",
    "Gluten-free options only",
    "Guest is vegetarian",
    "Please provide extra napkins",
    "Guest requested no onions in any dish",
    "Anniversary dinner — complimentary card on table",
    "Allergies: shellfish and dairy",
    "Rush order — guest checking out soon",
    "Cutlery for a child please",
    "Room service — leave at door, do not knock",
]

ITEM_NOTES = [
    "No ice",
    "Extra sauce on the side",
    "Well done",
    "Medium rare",
    "No onions",
    "Extra spicy",
    "Gluten-free bread if available",
    "No milk",
    "Light on salt",
    "Dressing on the side",
    "Add lemon",
    "No garnish",
    "Extra hot",
    "Half portion if possible",
    "Allergy: nuts",
]

# Indian Standard Time. Order times: 2:00 PM–2:40 PM on 3 Mar 2026 (IST).
IST = ZoneInfo("Asia/Kolkata")
ORDER_TIME_START = datetime(2026, 3, 3, 14, 0, 0, tzinfo=IST)   # 2:00 PM
ORDER_TIME_END = datetime(2026, 3, 3, 14, 40, 0, tzinfo=IST)   # 2:40 PM


def _random_created_at_recent() -> datetime:
    """Random created_at between 2:00 PM and 2:40 PM on 3 Mar 2026 (IST); stored as naive UTC."""
    delta_seconds = random.randint(0, 40 * 60)  # 0 to 40 minutes
    created_ist = ORDER_TIME_START + timedelta(seconds=delta_seconds)
    created_utc = created_ist.astimezone(timezone.utc).replace(tzinfo=None)
    return created_utc


# ---------------------------------------------------------------------------
# Main seed coroutine
# ---------------------------------------------------------------------------
ORDERS_PER_RESTAURANT = (10, 18)
STATUS_WEIGHTS = {
    OrderStatus.received: 20,
    OrderStatus.preparing: 15,
    OrderStatus.ready: 15,
    OrderStatus.served: 40,
    OrderStatus.cancelled: 10,
}
STATUSES = list(STATUS_WEIGHTS.keys())
STATUS_CUM_WEIGHTS = list(STATUS_WEIGHTS.values())


async def seed_orders(*, clear: bool = False) -> None:
    async with async_session_maker() as session:
        # ── Optionally clear ──────────────────────────────────────────
        if clear:
            await session.execute(delete(Order))
            await session.flush()
            print("Cleared existing orders.")
        else:
            count = (await session.execute(select(func.count(Order.id)))).scalar() or 0
            if count > 0:
                print(
                    f"Database already contains {count} orders. "
                    "Run with --clear to replace them, or drop tables and re-seed."
                )
                return

        # ── Load reference data ───────────────────────────────────────
        restaurants: list[Restaurant] = list(
            (await session.execute(select(Restaurant).order_by(Restaurant.name))).scalars().all()
        )
        if not restaurants:
            print("No restaurants found. Run python -m scripts.seed first.")
            return

        room_numbers: list[str] = [
            r.room_number
            for r in (await session.execute(select(Room).order_by(Room.room_number))).scalars().all()
        ]
        if not room_numbers:
            print("No rooms found. Run python -m scripts.seed first.")
            return

        menu_by_resto: dict[str, list[MenuItem]] = {}
        for resto in restaurants:
            result = await session.execute(
                select(MenuItem)
                .where(MenuItem.restaurant_id == resto.id)
                .options(selectinload(MenuItem.options))
            )
            menu_by_resto[str(resto.id)] = list(result.scalars().all())

        total_orders = 0

        for resto in restaurants:
            items_pool = menu_by_resto[str(resto.id)]
            if not items_pool:
                continue

            n_orders = random.randint(*ORDERS_PER_RESTAURANT)

            for _ in range(n_orders):
                # ── Pick order-level fields ────────────────────────
                room_id = random.choice(room_numbers)
                party_size = random.randint(1, 6)
                payment = (
                    PaymentMethod.room_bill
                    if random.random() < 0.70
                    else PaymentMethod.pay_now
                )
                status = random.choices(STATUSES, weights=STATUS_CUM_WEIGHTS, k=1)[0]
                created_at = _random_created_at_recent()

                order_notes = (
                    random.choice(ORDER_NOTES) if random.random() < 0.18 else None
                )

                # ── Build order items ─────────────────────────────
                n_lines = random.randint(1, min(5, len(items_pool)))
                chosen_items = random.sample(items_pool, n_lines)

                subtotal = Decimal("0")
                order_item_records: list[OrderItem] = []
                option_links: list[tuple[OrderItem, list]] = []

                for mi in chosen_items:
                    qty = random.randint(1, 3)
                    unit_price = mi.price

                    selected_opts = []
                    if mi.options:
                        if mi.requires_option_selection:
                            selected_opts = [random.choice(mi.options)]
                        elif random.random() < 0.40:
                            n_opts = random.randint(1, min(2, len(mi.options)))
                            selected_opts = random.sample(mi.options, n_opts)

                    for opt in selected_opts:
                        unit_price += opt.price_delta

                    item_notes = (
                        random.choice(ITEM_NOTES) if random.random() < 0.12 else None
                    )

                    oi = OrderItem(
                        id=uuid4(),
                        menu_item_id=mi.id,
                        name=mi.name,
                        unit_price=unit_price,
                        quantity=qty,
                        notes=item_notes,
                    )
                    order_item_records.append(oi)
                    if selected_opts:
                        option_links.append((oi, selected_opts))

                    subtotal += unit_price * qty

                # ── Persist order ─────────────────────────────────
                order = Order(
                    id=uuid4(),
                    restaurant_id=resto.id,
                    room_id=room_id,
                    party_size=party_size,
                    payment_method=payment,
                    status=status,
                    subtotal=subtotal,
                    notes=order_notes,
                    created_at=created_at,
                )
                session.add(order)
                await session.flush()

                for oi in order_item_records:
                    oi.order_id = order.id
                    session.add(oi)
                await session.flush()

                for oi, opts in option_links:
                    for opt in opts:
                        session.add(
                            OrderItemOption(
                                id=uuid4(),
                                order_item_id=oi.id,
                                menu_item_option_id=opt.id,
                            )
                        )
                await session.flush()

                total_orders += 1

        await session.commit()

        # ── Summary ───────────────────────────────────────────────────
        status_counts: dict[str, int] = {}
        for s in OrderStatus:
            cnt = (
                await session.execute(
                    select(func.count(Order.id)).where(Order.status == s)
                )
            ).scalar() or 0
            status_counts[s.value] = cnt

        print(f"Seeded {total_orders} orders across {len(restaurants)} restaurants.")
        print("Status breakdown:", status_counts)


if __name__ == "__main__":
    do_clear = "--clear" in sys.argv
    asyncio.run(seed_orders(clear=do_clear))
