"""Database Models"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

# ===================== ENUMS =====================
class UserRole(str, Enum):
    ADMIN = "admin"
    PROVIDER = "provider"
    USER = "user"

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"

# ===================== SCHEMAS =====================
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    sku: str
    category: str

class ProductCreate(ProductBase):
    provider_id: str

class Product(ProductBase):
    id: str = Field(alias="_id")
    provider_id: str
    created_at: datetime
    updated_at: datetime
    stock_history: List[dict] = []  # Track stock changes
    
    class Config:
        from_attributes = True

# ===================== USER =====================
class UserBase(BaseModel):
    email: str
    username: str
    role: UserRole

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True

# ===================== ORDER =====================
class OrderItemBase(BaseModel):
    product_id: str
    quantity: int
    price_at_purchase: float

class OrderCreate(BaseModel):
    items: List[OrderItemBase]
    shipping_address: str
    payment_method: str

class Order(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    provider_id: str
    items: List[OrderItemBase]
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    total_amount: float
    created_at: datetime
    updated_at: datetime
    shipping_address: str
    idempotency_key: Optional[str] = None  # ป้องกัน duplicate purchases
    
    class Config:
        from_attributes = True

# ===================== TRANSACTION LOG (Duplicate Purchase Prevention) =====================
class TransactionLog(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    product_id: str
    quantity: int
    idempotency_key: str
    timestamp: datetime
    status: str  # 'success', 'failed', 'pending'
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

# ===================== INVENTORY TRACKING =====================
class InventoryLog(BaseModel):
    id: str = Field(alias="_id")
    product_id: str
    provider_id: str
    action: str  # 'add', 'remove', 'sold'
    quantity_changed: int
    old_stock: int
    new_stock: int
    reference_id: Optional[str] = None  # order_id or restock_id
    timestamp: datetime
    reason: str

    class Config:
        from_attributes = True

# ===================== DASHBOARD =====================
class DashboardSummary(BaseModel):
    total_products: int
    total_stock: int
    low_stock_items: List[dict]
    total_revenue: float
    total_orders: int
    orders_today: int
    sales_by_product: List[dict]
    sales_trend: List[dict]  # Last 7 days
