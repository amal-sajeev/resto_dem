from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth import get_establishment_id
from app.database import get_db
from app.models import MenuItem, MenuItemOption, Order, OrderItem, OrderItemOption, OrderStatus, Restaurant
from app.schemas import (
    KitchenOrderEdit,
    OrderItemOptionResponse,
    OrderItemResponse,
    OrderListResponse,
    OrderStatusUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/kitchen", tags=["kitchen"])


def _order_to_list_response(order: Order) -> OrderListResponse:
    items_data = []
    for item in order.items:
        options_data = []
        for oio in item.options:
            opt = oio.menu_item_option
            options_data.append(
                OrderItemOptionResponse(
                    id=oio.id,
                    menu_item_option_id=oio.menu_item_option_id,
                    label=opt.label if opt else None,
                    price_delta=opt.price_delta if opt else None,
                )
            )
        items_data.append(
            OrderItemResponse(
                id=item.id,
                menu_item_id=item.menu_item_id,
                name=item.name,
                unit_price=item.unit_price,
                quantity=item.quantity,
                notes=item.notes,
                options=options_data,
            )
        )
    return OrderListResponse(
        id=order.id,
        restaurant_id=order.restaurant_id,
        room_id=order.room_id,
        party_size=order.party_size,
        payment_method=order.payment_method,
        status=order.status,
        subtotal=order.subtotal,
        notes=order.notes,
        created_at=order.created_at,
        items=items_data,
    )


def _load_order_with_options(q):
    return q.options(
        selectinload(Order.items).selectinload(OrderItem.options).selectinload(OrderItemOption.menu_item_option)
    )


@router.get("/orders", response_model=list[OrderListResponse])
async def list_kitchen_orders(
    request: Request,
    restaurant_id: UUID = Query(..., description="Filter by restaurant"),
    db: AsyncSession = Depends(get_db),
) -> list[OrderListResponse]:
    est_id = get_establishment_id(request)
    rest_check = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id, Restaurant.establishment_id == est_id)
    )
    if rest_check.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Restaurant not found in this establishment")
    q = (
        select(Order)
        .where(Order.restaurant_id == restaurant_id)
        .where(Order.status != OrderStatus.cancelled)
        .order_by(Order.created_at.desc())
    )
    q = _load_order_with_options(q)
    result = await db.execute(q)
    orders = list(result.scalars().all())
    return [_order_to_list_response(o) for o in orders]


@router.patch("/orders/{order_id}", response_model=OrderListResponse)
async def update_order_status(
    order_id: UUID,
    body: OrderStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    est_id = get_establishment_id(request)
    result = await db.execute(
        _load_order_with_options(
            select(Order)
            .join(Restaurant, Order.restaurant_id == Restaurant.id)
            .where(Order.id == order_id, Restaurant.establishment_id == est_id)
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = body.status
    await db.flush()
    await db.refresh(order)
    result2 = await db.execute(
        _load_order_with_options(select(Order).where(Order.id == order_id))
    )
    order = result2.scalar_one()
    return _order_to_list_response(order)


@router.put("/orders/{order_id}/edit", response_model=OrderListResponse)
async def edit_order(
    order_id: UUID,
    body: KitchenOrderEdit,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    est_id = get_establishment_id(request)
    result = await db.execute(
        _load_order_with_options(
            select(Order)
            .join(Restaurant, Order.restaurant_id == Restaurant.id)
            .where(Order.id == order_id, Restaurant.establishment_id == est_id)
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status in (OrderStatus.cancelled, OrderStatus.served):
        raise HTTPException(
            status_code=400,
            detail="Cannot edit a cancelled or served order.",
        )

    existing_items = {item.id: item for item in order.items}

    for item_id in body.items_to_remove:
        item = existing_items.get(item_id)
        if item:
            await db.delete(item)
            del existing_items[item_id]

    for upd in body.items_to_update:
        item = existing_items.get(upd.item_id)
        if not item:
            continue
        if upd.quantity is not None:
            item.quantity = upd.quantity
        if upd.notes is not None:
            item.notes = upd.notes if upd.notes else None

    for add in body.items_to_add:
        mi_result = await db.execute(
            select(MenuItem).where(
                MenuItem.id == add.menu_item_id,
                MenuItem.restaurant_id == order.restaurant_id,
            )
        )
        mi = mi_result.scalar_one_or_none()
        if not mi:
            raise HTTPException(
                status_code=400,
                detail=f"Menu item {add.menu_item_id} not found in this restaurant.",
            )
        new_item = OrderItem(
            order_id=order.id,
            menu_item_id=mi.id,
            name=mi.name,
            unit_price=mi.price,
            quantity=add.quantity,
            notes=add.notes,
        )
        db.add(new_item)
        await db.flush()

        if add.option_ids:
            opt_result = await db.execute(
                select(MenuItemOption).where(
                    MenuItemOption.id.in_(add.option_ids),
                    MenuItemOption.menu_item_id == mi.id,
                )
            )
            for opt in opt_result.scalars().all():
                db.add(OrderItemOption(
                    order_item_id=new_item.id,
                    menu_item_option_id=opt.id,
                ))

    if body.notes is not None:
        order.notes = body.notes if body.notes else None

    await db.flush()
    refresh_result = await db.execute(
        _load_order_with_options(select(Order).where(Order.id == order_id))
    )
    order = refresh_result.scalar_one()
    order.subtotal = sum(
        it.unit_price * it.quantity for it in order.items
    ) or Decimal("0.00")
    await db.flush()
    await db.refresh(order)

    final_result = await db.execute(
        _load_order_with_options(select(Order).where(Order.id == order_id))
    )
    order = final_result.scalar_one()
    return _order_to_list_response(order)
