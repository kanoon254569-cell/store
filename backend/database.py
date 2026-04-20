"""Database Connection and Operations"""
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import uuid

class Database:
    client = None
    db = None

db = Database()

async def connect_to_mongo():
    """Connect to MongoDB"""
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db.db = db.client[settings.DATABASE_NAME]
    print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")

async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        print("❌ Disconnected from MongoDB")

# ===================== DATABASE OPERATIONS =====================

class UserDB:
    @staticmethod
    async def create_user(user_data: dict):
        """Create new user"""
        user_data["created_at"] = datetime.utcnow()
        user_data["updated_at"] = datetime.utcnow()
        result = await db.db["users"].insert_one(user_data)
        return str(result.inserted_id)
    
    @staticmethod
    async def get_user_by_email(email: str):
        """Get user by email"""
        return await db.db["users"].find_one({"email": email})
    
    @staticmethod
    async def get_user_by_id(user_id: str):
        """Get user by ID"""
        from bson import ObjectId
        return await db.db["users"].find_one({"_id": ObjectId(user_id)})

class ProductDB:
    @staticmethod
    async def create_product(product_data: dict):
        """Create new product"""
        product_data["created_at"] = datetime.utcnow()
        product_data["updated_at"] = datetime.utcnow()
        product_data["stock_history"] = []
        result = await db.db["products"].insert_one(product_data)
        return str(result.inserted_id)
    
    @staticmethod
    async def get_product_by_id(product_id: str):
        """Get product by ID"""
        from bson import ObjectId
        return await db.db["products"].find_one({"_id": ObjectId(product_id)})
    
    @staticmethod
    async def get_product_by_sku(sku: str):
        """Get product by SKU"""
        return await db.db["products"].find_one({"sku": sku})
    
    @staticmethod
    async def get_products_by_provider(provider_id: str):
        """Get all products by provider"""
        return await db.db["products"].find({"provider_id": provider_id}).to_list(None)
    
    @staticmethod
    async def update_product_stock(product_id: str, quantity_change: int, reason: str):
        """
        Update product stock with logging
        quantity_change: positive (add), negative (remove)
        """
        from bson import ObjectId
        product = await db.db["products"].find_one({"_id": ObjectId(product_id)})
        
        if not product:
            return None
        
        old_stock = product["stock"]
        new_stock = old_stock + quantity_change
        
        if new_stock < 0:
            return {"error": "Stock cannot be negative", "code": "INSUFFICIENT_STOCK"}
        
        # Update stock
        updated = await db.db["products"].update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"stock": new_stock, "updated_at": datetime.utcnow()}}
        )
        
        # Log to inventory history
        await InventoryDB.log_stock_change(
            product_id=product_id,
            provider_id=product.get("provider_id"),
            old_stock=old_stock,
            new_stock=new_stock,
            quantity_changed=quantity_change,
            reason=reason
        )
        
        return {"old_stock": old_stock, "new_stock": new_stock, "success": True}

class OrderDB:
    @staticmethod
    async def create_order(order_data: dict):
        """Create new order with idempotency key"""
        from bson import ObjectId
        
        # Generate idempotency key if not exists
        if not order_data.get("idempotency_key"):
            order_data["idempotency_key"] = str(uuid.uuid4())
        
        order_data["created_at"] = datetime.utcnow()
        order_data["updated_at"] = datetime.utcnow()
        
        result = await db.db["orders"].insert_one(order_data)
        return str(result.inserted_id)
    
    @staticmethod
    async def get_order_by_id(order_id: str):
        """Get order by ID"""
        from bson import ObjectId
        return await db.db["orders"].find_one({"_id": ObjectId(order_id)})
    
    @staticmethod
    async def get_orders_by_user(user_id: str):
        """Get all orders by user"""
        return await db.db["orders"].find({"user_id": user_id}).to_list(None)
    
    @staticmethod
    async def get_orders_by_provider(provider_id: str):
        """Get all orders for a provider"""
        return await db.db["orders"].find({"provider_id": provider_id}).to_list(None)
    
    @staticmethod
    async def update_order_status(order_id: str, status: str):
        """Update order status"""
        from bson import ObjectId
        await db.db["orders"].update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )

class TransactionLogDB:
    @staticmethod
    async def log_transaction(
        user_id: str,
        product_id: str,
        quantity: int,
        idempotency_key: str,
        status: str,
        error_message: Optional[str] = None
    ):
        """Log transaction for duplicate prevention"""
        log_data = {
            "user_id": user_id,
            "product_id": product_id,
            "quantity": quantity,
            "idempotency_key": idempotency_key,
            "timestamp": datetime.utcnow(),
            "status": status,
            "error_message": error_message
        }
        
        await db.db["transaction_logs"].insert_one(log_data)
    
    @staticmethod
    async def check_duplicate_purchase(idempotency_key: str, user_id: str):
        """
        Check if this purchase was already processed
        Returns: existing transaction if found, None otherwise
        """
        return await db.db["transaction_logs"].find_one({
            "idempotency_key": idempotency_key,
            "user_id": user_id,
            "status": "success"
        })
    
    @staticmethod
    async def get_user_purchases_last_minute(user_id: str):
        """Get user's purchases in the last minute (rate limiting check)"""
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        return await db.db["transaction_logs"].find({
            "user_id": user_id,
            "timestamp": {"$gte": one_minute_ago},
            "status": "success"
        }).to_list(None)

class InventoryDB:
    @staticmethod
    async def log_stock_change(
        product_id: str,
        provider_id: str,
        old_stock: int,
        new_stock: int,
        quantity_changed: int,
        reason: str,
        reference_id: Optional[str] = None
    ):
        """Log inventory changes"""
        log = {
            "product_id": product_id,
            "provider_id": provider_id,
            "action": "add" if quantity_changed > 0 else "remove",
            "quantity_changed": quantity_changed,
            "old_stock": old_stock,
            "new_stock": new_stock,
            "reference_id": reference_id,
            "timestamp": datetime.utcnow(),
            "reason": reason
        }
        
        await db.db["inventory_logs"].insert_one(log)
    
    @staticmethod
    async def get_inventory_history(product_id: str, days: int = 30):
        """Get inventory history for a product"""
        date_threshold = datetime.utcnow() - timedelta(days=days)
        return await db.db["inventory_logs"].find({
            "product_id": product_id,
            "timestamp": {"$gte": date_threshold}
        }).to_list(None)

class DashboardDB:
    @staticmethod
    async def get_provider_dashboard(provider_id: str):
        """Get dashboard summary for provider"""
        from bson import ObjectId
        
        # Total products and stock
        products = await db.db["products"].find(
            {"provider_id": provider_id}
        ).to_list(None)
        
        total_products = len(products)
        total_stock = sum(p.get("stock", 0) for p in products)
        
        # Low stock items (< 5)
        low_stock = [p for p in products if p.get("stock", 0) < 5]
        
        # Total revenue and orders
        orders = await db.db["orders"].find({
            "provider_id": provider_id,
            "status": {"$ne": "cancelled"}
        }).to_list(None)
        
        total_revenue = sum(o.get("total_amount", 0) for o in orders)
        total_orders = len(orders)
        
        # Orders today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        orders_today = len([o for o in orders if o.get("created_at", datetime.min) >= today_start])
        
        # Sales by product
        sales_by_product = []
        for product in products:
            product_sales = sum(
                sum(item.get("quantity", 0) for item in o.get("items", []) 
                    if item.get("product_id") == str(product.get("_id")))
                for o in orders
            )
            sales_by_product.append({
                "product": product.get("name"),
                "sales": product_sales,
                "revenue": product_sales * product.get("price", 0)
            })
        
        return {
            "total_products": total_products,
            "total_stock": total_stock,
            "low_stock_items": low_stock,
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "orders_today": orders_today,
            "sales_by_product": sales_by_product
        }
