from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_establishment_id
from app.database import get_db
from app.models import MenuItem, MenuItemOption, Order, OrderItem, OrderItemOption, OrderStatus, Restaurant
from app.schemas import OrderCreate, OrderItemOptionResponse, OrderItemResponse, OrderListResponse, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])

IN_PROGRESS_STATUSES = (OrderStatus.received, OrderStatus.preparing, OrderStatus.ready)


def _order_to_response(order: Order) -> OrderResponse:
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
    return OrderResponse(
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


@router.get("", response_model=list[OrderListResponse])
async def list_orders(
    request: Request,
    room_id: Optional[str] = Query(None, description="Filter by room"),
    restaurant_id: Optional[UUID] = Query(None, description="Filter by restaurant"),
    status: Optional[OrderStatus] = Query(None, description="Filter by status"),
    in_progress: bool = Query(False, description="If true, only orders with status received/preparing/ready"),
    from_date: Optional[date] = Query(None, description="Orders from this date (inclusive)"),
    to_date: Optional[date] = Query(None, description="Orders until this date (inclusive)"),
    db: AsyncSession = Depends(get_db),
) -> list[OrderListResponse]:
    est_id = get_establishment_id(request)
    q = (
        select(Order)
        .join(Restaurant, Order.restaurant_id == Restaurant.id)
        .where(Restaurant.establishment_id == est_id)
        .order_by(Order.created_at.desc())
    )
    if room_id is not None:
        q = q.where(Order.room_id == room_id)
    if restaurant_id is not None:
        q = q.where(Order.restaurant_id == restaurant_id)
    if in_progress:
        q = q.where(Order.status.in_(IN_PROGRESS_STATUSES))
    elif status is not None:
        q = q.where(Order.status == status)
    if from_date is not None:
        q = q.where(Order.created_at >= datetime(from_date.year, from_date.month, from_date.day))
    if to_date is not None:
        end_of_day = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59, 999999)
        q = q.where(Order.created_at <= end_of_day)
    q = _load_order_with_options(q)
    result = await db.execute(q)
    orders = list(result.scalars().all())
    return [_order_to_list_response(o) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
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
    return _order_to_response(order)


@router.post("", response_model=OrderResponse)
async def create_order(
    body: OrderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    est_id = get_establishment_id(request)
    r = await db.execute(
        select(Restaurant).where(Restaurant.id == body.restaurant_id, Restaurant.establishment_id == est_id)
    )
    restaurant = r.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    menu_item_ids = [i.menu_item_id for i in body.items]
    unique_menu_item_ids = set(menu_item_ids)
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id.in_(unique_menu_item_ids),
            MenuItem.restaurant_id == body.restaurant_id,
        )
    )
    menu_items = {m.id: m for m in result.scalars().all()}
    missing = unique_menu_item_ids - set(menu_items.keys())
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Menu item(s) not found or not in this restaurant: {missing}",
        )

    subtotal = Decimal("0")
    order_items: list[OrderItem] = []
    order_item_options_to_add: list[tuple[OrderItem, list[MenuItemOption]]] = []

    for line in body.items:
        mi = menu_items[line.menu_item_id]
        qty = line.quantity
        unit_price = mi.price
        selected_options: list[MenuItemOption] = []

        if mi.requires_option_selection and (not line.option_ids or len(line.option_ids) == 0):
            raise HTTPException(
                status_code=400,
                detail=f"Menu item '{mi.name}' requires selecting an option.",
            )

        if line.option_ids:
            opt_result = await db.execute(
                select(MenuItemOption).where(
                    MenuItemOption.id.in_(line.option_ids),
                    MenuItemOption.menu_item_id == line.menu_item_id,
                )
            )
            selected_options = list(opt_result.scalars().all())
            if len(selected_options) != len(line.option_ids):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid or duplicate option_ids for menu item {line.menu_item_id}",
                )
            for opt in selected_options:
                unit_price += opt.price_delta

        subtotal += unit_price * qty
        oi = OrderItem(
            menu_item_id=mi.id,
            name=mi.name,
            unit_price=unit_price,
            quantity=qty,
            notes=line.notes,
        )
        order_items.append(oi)
        if selected_options:
            order_item_options_to_add.append((oi, selected_options))

    order = Order(
        restaurant_id=body.restaurant_id,
        room_id=body.room_id,
        party_size=body.party_size,
        payment_method=body.payment_method,
        status=OrderStatus.received,
        subtotal=subtotal,
        notes=body.notes,
    )
    db.add(order)
    await db.flush()

    for oi in order_items:
        oi.order_id = order.id
        db.add(oi)
    await db.flush()

    for oi, opts in order_item_options_to_add:
        for opt in opts:
            db.add(OrderItemOption(order_item_id=oi.id, menu_item_option_id=opt.id))
    await db.flush()

    result = await db.execute(
        _load_order_with_options(select(Order).where(Order.id == order.id))
    )
    loaded_order = result.scalar_one()
    return _order_to_response(loaded_order)


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
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
    if order.status not in (OrderStatus.received, OrderStatus.preparing, OrderStatus.ready):
        raise HTTPException(
            status_code=400,
            detail="Order cannot be cancelled at this stage.",
        )
    order.status = OrderStatus.cancelled
    await db.flush()
    await db.refresh(order)
    result2 = await db.execute(
        _load_order_with_options(select(Order).where(Order.id == order_id))
    )
    order = result2.scalar_one()
    return _order_to_response(order)
