from datetime import datetime, time
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import OrderStatus, PaymentMethod


# ----- Restaurant -----
class RestaurantBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    open_from: Optional[time] = None
    open_until: Optional[time] = None


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    open_from: Optional[time] = None
    open_until: Optional[time] = None


class RestaurantResponse(RestaurantBase):
    id: UUID

    model_config = {"from_attributes": True}


# ----- MenuItem -----
class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    category: str
    image_url: Optional[str] = None
    allergens: Optional[str] = None
    requires_option_selection: bool = False


class MenuItemCreate(MenuItemBase):
    restaurant_id: UUID


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    allergens: Optional[str] = None
    requires_option_selection: Optional[bool] = None


class MenuItemResponse(MenuItemBase):
    id: UUID
    restaurant_id: UUID
    options: list["MenuItemOptionResponse"] = []

    model_config = {"from_attributes": True}


# ----- MenuItemOption -----
class MenuItemOptionResponse(BaseModel):
    id: UUID
    label: str
    price_delta: Decimal

    model_config = {"from_attributes": True}


# ----- Order -----
class OrderItemCreate(BaseModel):
    menu_item_id: UUID
    quantity: int = Field(..., ge=1)
    notes: Optional[str] = None
    option_ids: Optional[list[UUID]] = None


class OrderItemResponse(BaseModel):
    id: UUID
    menu_item_id: UUID
    name: str
    unit_price: Decimal
    quantity: int
    notes: Optional[str] = None
    options: list["OrderItemOptionResponse"] = []

    model_config = {"from_attributes": True}


class OrderItemOptionResponse(BaseModel):
    id: UUID
    menu_item_option_id: UUID
    label: Optional[str] = None
    price_delta: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    restaurant_id: UUID
    room_id: str
    party_size: int = Field(..., ge=1, le=50)
    payment_method: PaymentMethod
    items: list[OrderItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: UUID
    restaurant_id: UUID
    room_id: str
    party_size: int
    payment_method: PaymentMethod
    status: OrderStatus
    subtotal: Decimal
    notes: Optional[str] = None
    created_at: datetime
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    id: UUID
    restaurant_id: UUID
    room_id: str
    party_size: int
    payment_method: PaymentMethod
    status: OrderStatus
    subtotal: Decimal
    notes: Optional[str] = None
    created_at: datetime
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# ----- Kitchen order editing -----
class KitchenItemAdd(BaseModel):
    menu_item_id: UUID
    quantity: int = Field(..., ge=1)
    notes: Optional[str] = None
    option_ids: Optional[list[UUID]] = None


class KitchenItemUpdate(BaseModel):
    item_id: UUID
    quantity: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None


class KitchenOrderEdit(BaseModel):
    notes: Optional[str] = None
    items_to_add: list[KitchenItemAdd] = []
    items_to_update: list[KitchenItemUpdate] = []
    items_to_remove: list[UUID] = []


# ----- Room -----
class RoomCreate(BaseModel):
    room_number: str
    display_name: Optional[str] = None


class RoomResponse(BaseModel):
    id: UUID
    room_number: str
    display_name: Optional[str] = None

    model_config = {"from_attributes": True}
