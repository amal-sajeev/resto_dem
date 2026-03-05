from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models import OrderStatus, PaymentMethod, ReservationStatus, UserRole


# ----- Establishment -----
class EstablishmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")


class EstablishmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")
    is_active: Optional[bool] = None


class EstablishmentResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    room_theme: str
    kitchen_theme: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EstablishmentStats(BaseModel):
    total_establishments: int
    active_establishments: int
    total_orders: int
    total_restaurants: int


# ----- Branding -----
class BrandingResponse(BaseModel):
    name: str
    logo_url: Optional[str] = None
    room_theme: str
    kitchen_theme: str
    custom_room_colors: Optional[dict] = None
    custom_kitchen_colors: Optional[dict] = None


class BrandingUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=512)
    room_theme: Optional[str] = Field(None, max_length=64)
    kitchen_theme: Optional[str] = Field(None, max_length=64)
    custom_room_colors: Optional[dict] = None
    custom_kitchen_colors: Optional[dict] = None


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


# ----- Auth -----
class OTPRequest(BaseModel):
    phone: str = Field(..., min_length=7, max_length=20)


class OTPVerify(BaseModel):
    phone: str = Field(..., min_length=7, max_length=20)
    code: str = Field(..., min_length=6, max_length=6)
    name: Optional[str] = Field(None, min_length=1, max_length=128)


class StaffLogin(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: UUID
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    role: UserRole
    establishment_id: Optional[UUID] = None
    restaurant_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ----- Table -----
class TableCreate(BaseModel):
    restaurant_id: UUID
    table_number: str = Field(..., min_length=1, max_length=32)
    capacity: int = Field(..., ge=1, le=50)


class TableUpdate(BaseModel):
    table_number: Optional[str] = Field(None, min_length=1, max_length=32)
    capacity: Optional[int] = Field(None, ge=1, le=50)
    is_active: Optional[bool] = None


class TableResponse(BaseModel):
    id: UUID
    restaurant_id: UUID
    table_number: str
    capacity: int
    is_active: bool

    model_config = {"from_attributes": True}


# ----- Reservation -----
class ReservationCreate(BaseModel):
    restaurant_id: UUID
    table_id: UUID
    reservation_date: date
    reservation_time: time
    party_size: int = Field(..., ge=1, le=50)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def time_on_the_hour(self) -> "ReservationCreate":
        if self.reservation_time.minute != 0 or self.reservation_time.second != 0:
            raise ValueError("reservation_time must be on the hour (e.g. 13:00)")
        return self


class ReservationResponse(BaseModel):
    id: UUID
    user_id: UUID
    restaurant_id: UUID
    table_id: UUID
    reservation_date: date
    reservation_time: time
    party_size: int
    status: ReservationStatus
    confirmation_code: str
    notes: Optional[str] = None
    created_at: datetime
    user_name: Optional[str] = None
    restaurant_name: Optional[str] = None
    table_number: Optional[str] = None

    model_config = {"from_attributes": True}


class ReservationStatusUpdate(BaseModel):
    status: ReservationStatus


class SlotsResponse(BaseModel):
    slots: list[str]
    booked: dict[str, list[UUID]]


# ----- Staff / Admin -----
class StaffCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    role: UserRole
    restaurant_id: Optional[UUID] = None


class StaffUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    email: Optional[str] = Field(None, min_length=5, max_length=255)
    role: Optional[UserRole] = None
    restaurant_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class StaffResponse(BaseModel):
    id: UUID
    name: str
    email: Optional[str] = None
    role: UserRole
    establishment_id: Optional[UUID] = None
    restaurant_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ----- Superadmin: seed admin for establishment -----
class SeedAdminCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
