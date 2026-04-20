"""Main FastAPI Application"""
from fastapi import FastAPI, HTTPException, status, Depends, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from datetime import timedelta
import uvicorn
import os

from .config import settings
from .database import (
    connect_to_mongo, close_mongo_connection, db,
    UserDB, ProductDB, OrderDB, TransactionLogDB, InventoryDB, DashboardDB
)
from .security import (
    create_access_token, get_current_user, duplicate_prevention,
    db_rate_limiter, validate_stock_availability, idempotency_handler
)
from .models import (
    UserCreate, User, ProductCreate, Product, OrderCreate, Order,
    UserRole, OrderStatus, PaymentStatus
)
from .data_loader import load_excel_data, seed_database
from typing import Optional, List
from bson import ObjectId
import uuid
import bcrypt

# ===================== LIFESPAN =====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    print("🚀 FastAPI Server Started")
    
    # Auto-load Excel data on startup
    try:
        # Check if products already exist
        existing_products = await db.db["products"].count_documents({})
        if existing_products == 0:
            print("📊 No products found in database, loading from Excel...")
            
            # Try multiple possible paths (from /app working directory)
            possible_paths = [
                "backend/Adidas US Sales Datasets.xlsx",        # In Docker
                "Adidas US Sales Datasets.xlsx",                # In backend/ directory
                "../Adidas US Sales Datasets.xlsx",
                "../../Adidas US Sales Datasets.xlsx",
            ]
            
            excel_path = None
            for path in possible_paths:
                print(f"  🔍 Checking: {path}")
                if os.path.exists(path):
                    excel_path = path
                    print(f"  ✓ Found!")
                    break
            
            if excel_path:
                print(f"  📥 Loading from: {excel_path}")
                products = await load_excel_data(excel_path)
                if products:
                    result = await db.db["products"].insert_many(products)
                    print(f"✅ Loaded {len(result.inserted_ids)} products from Excel!")
                else:
                    print(f"❌ No products extracted from Excel")
            else:
                print(f"❌ Excel file not found")
                print(f"   CWD: {os.getcwd()}")
        else:
            print(f"✅ Database already has {existing_products} products")
    except Exception as e:
        import traceback
        print(f"❌ Error auto-loading Excel: {str(e)}")
        traceback.print_exc()
    
    yield
    # Shutdown
    await close_mongo_connection()
    print("🛑 FastAPI Server Stopped")

# ===================== CREATE APP =====================

app = FastAPI(
    title="E-Commerce Admin/Provider/User API",
    description="Multi-vendor e-commerce system with stock protection & rate limiting",
    version="1.0.0",
    lifespan=lifespan
)

# ===================== CORS =====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== AUTHENTICATION ROUTES =====================

@app.post("/api/auth/register")
async def register(user: UserCreate):
    """Register new user"""
    # Check if email exists
    existing = await UserDB.get_user_by_email(user.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_pw = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
    
    user_data = {
        "email": user.email,
        "username": user.username,
        "password_hash": hashed_pw.decode(),
        "role": user.role,
        "is_active": True
    }
    
    user_id = await UserDB.create_user(user_data)
    
    # Create access token
    access_token = create_access_token({"sub": user_id})
    
    return {
        "user_id": user_id,
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.post("/api/auth/login")
async def login(email: str = Query(...), password: str = Query(...)):
    """Login user"""
    user = await UserDB.get_user_by_email(email)
    
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token({"sub": str(user["_id"])})
    
    return {
        "user_id": str(user["_id"]),
        "access_token": access_token,
        "token_type": "bearer"
    }

# ===================== ADMIN DASHBOARD ROUTES =====================

@app.get("/api/admin/dashboard")
async def admin_dashboard(current_user: str = Depends(get_current_user)):
    """Get admin dashboard (SKU summary + sales overview)"""
    await db_rate_limiter.check_circuit_breaker()
    
    if not await db_rate_limiter.check_user_rate(current_user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Get all products (admin can see all)
    from .database import db
    products = await db.db["products"].find({}).to_list(None)
    
    # Calculate totals
    total_products = len(products)
    total_stock = sum(p.get("stock", 0) for p in products)
    
    # Get all orders
    orders = await db.db["orders"].find({}).to_list(None)
    total_revenue = sum(o.get("total_amount", 0) for o in orders)
    total_orders = len(orders)
    
    # SKU Summary
    sku_summary = [
        {
            "sku": p.get("sku"),
            "product_name": p.get("name"),
            "provider": p.get("provider_id"),
            "stock": p.get("stock", 0),
            "price": p.get("price"),
            "total_value": p.get("stock", 0) * p.get("price", 0)
        }
        for p in products
    ]
    
    return {
        "total_products": total_products,
        "total_stock": total_stock,
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "sku_summary": sku_summary
    }

@app.get("/api/admin/inventory-status")
async def admin_inventory_status(current_user: str = Depends(get_current_user)):
    """Get inventory status with alerts"""
    from .database import db
    
    products = await db.db["products"].find({}).to_list(None)
    
    # Categorize products
    critical_stock = [p for p in products if p.get("stock", 0) == 0]
    low_stock = [p for p in products if 0 < p.get("stock", 0) < 5]
    good_stock = [p for p in products if p.get("stock", 0) >= 5]
    
    return {
        "critical_stock": {
            "count": len(critical_stock),
            "items": critical_stock
        },
        "low_stock": {
            "count": len(low_stock),
            "items": low_stock
        },
        "good_stock": {
            "count": len(good_stock)
        }
    }

# ===================== PROVIDER ROUTES (Add Products & Services) =====================

@app.post("/api/provider/products")
async def provider_create_product(
    product: ProductCreate,
    current_user: str = Depends(get_current_user)
):
    """Provider: Create new product"""
    await db_rate_limiter.check_circuit_breaker()
    
    if not await db_rate_limiter.check_user_rate(current_user):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)
    
    # Check if SKU exists
    existing = await ProductDB.get_product_by_sku(product.sku)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SKU already exists"
        )
    
    product_data = product.dict()
    product_data["provider_id"] = current_user
    
    product_id = await ProductDB.create_product(product_data)
    
    return {
        "product_id": product_id,
        "message": "Product created successfully"
    }

@app.put("/api/provider/products/{product_id}/stock")
async def provider_restock_product(
    product_id: str,
    quantity: int,
    reason: str = "Manual restock",
    current_user: str = Depends(get_current_user)
):
    """Provider: Add stock to product"""
    await db_rate_limiter.check_circuit_breaker()
    
    result = await ProductDB.update_product_stock(
        product_id=product_id,
        quantity_change=quantity,
        reason=reason
    )
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {"message": f"Added {quantity} units", "result": result}

@app.get("/api/provider/dashboard")
async def provider_dashboard(current_user: str = Depends(get_current_user)):
    """Provider: Get own dashboard"""
    dashboard = await DashboardDB.get_provider_dashboard(current_user)
    return dashboard

# ===================== USER SHOPPING ROUTES =====================

@app.get("/api/user/products")
async def user_browse_products(category: Optional[str] = None):
    """User: Browse products"""
    from .database import db
    
    query = {}
    if category:
        query["category"] = category
    
    products = await db.db["products"].find(query).to_list(None)
    
    # Convert ObjectId to string for JSON serialization
    for product in products:
        product["_id"] = str(product["_id"])
    
    return {"products": products}

@app.get("/api/user/search")
async def user_search_products(q: Optional[str] = None, category: Optional[str] = None):
    """User: Search products by name, SKU, or description"""
    from .database import db
    
    query = {}
    
    # Build search query
    if q:
        # Search in name, SKU, and description
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"sku": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}}
        ]
    
    if category:
        query["category"] = category
    
    products = await db.db["products"].find(query).to_list(None)
    
    # Convert ObjectId to string for JSON serialization
    for product in products:
        product["_id"] = str(product["_id"])
    
    return {
        "query": q,
        "category": category,
        "count": len(products),
        "products": products
    }

@app.get("/api/user/products/{product_id}")
async def user_get_product(product_id: str):
    """User: Get product details"""
    product = await ProductDB.get_product_by_id(product_id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product

@app.post("/api/user/orders")
async def user_create_order(
    order: OrderCreate,
    idempotency_key: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """
    User: Create order (with duplicate purchase prevention)
    
    ป้องกัน:
    1. Stock validation (ไม่ขายเกินจำนวน)
    2. Idempotency key (ถ้า request ซ้ำกันจะ return ผลเดิม)
    3. Rate limiting (ไม่ให้ซื้อเร็วเกินไป)
    """
    
    # === STEP 1: Check rate limiting & circuit breaker ===
    await db_rate_limiter.check_circuit_breaker()
    
    if not await db_rate_limiter.check_user_rate(current_user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests - please wait before placing another order"
        )
    
    # === STEP 2: Generate idempotency key if not provided ===
    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())
    
    # === STEP 3: Check if this request was already processed ===
    existing_result = await idempotency_handler.get_result(idempotency_key)
    if existing_result:
        return existing_result
    
    # === STEP 4: Check duplicate purchase from transaction log ===
    duplicate = await TransactionLogDB.check_duplicate_purchase(idempotency_key, current_user)
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate purchase detected"
        )
    
    # === STEP 5: Check purchase rate (same product) ===
    for item in order.items:
        allowed = await duplicate_prevention.check_purchase_rate(
            current_user, item.product_id
        )
        if not allowed:
            await TransactionLogDB.log_transaction(
                user_id=current_user,
                product_id=item.product_id,
                quantity=item.quantity,
                idempotency_key=idempotency_key,
                status="failed",
                error_message="Purchase rate limit exceeded"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Purchasing same product too quickly"
            )
    
    # === STEP 6: Validate stock for all items ===
    for item in order.items:
        if not await validate_stock_availability(item.product_id, item.quantity):
            await TransactionLogDB.log_transaction(
                user_id=current_user,
                product_id=item.product_id,
                quantity=item.quantity,
                idempotency_key=idempotency_key,
                status="failed",
                error_message="Insufficient stock"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {item.product_id}"
            )
    
    # === STEP 7: Calculate total and create order ===
    try:
        total_amount = sum(item.quantity * item.price_at_purchase for item in order.items)
        
        # Get provider_id from first product
        first_product = await ProductDB.get_product_by_id(order.items[0].product_id)
        provider_id = first_product.get("provider_id")
        
        order_data = {
            "user_id": current_user,
            "provider_id": provider_id,
            "items": [item.dict() for item in order.items],
            "status": OrderStatus.PENDING,
            "payment_status": PaymentStatus.PENDING,
            "total_amount": total_amount,
            "shipping_address": order.shipping_address,
            "payment_method": order.payment_method,
            "idempotency_key": idempotency_key
        }
        
        order_id = await OrderDB.create_order(order_data)
        
        # === STEP 8: Deduct stock ===
        for item in order.items:
            result = await ProductDB.update_product_stock(
                product_id=item.product_id,
                quantity_change=-item.quantity,
                reason=f"Order {order_id}"
            )
            
            if isinstance(result, dict) and "error" in result:
                raise Exception(f"Stock update failed: {result['error']}")
        
        # === STEP 9: Log successful transaction ===
        await TransactionLogDB.log_transaction(
            user_id=current_user,
            product_id=order.items[0].product_id,
            quantity=order.items[0].quantity,
            idempotency_key=idempotency_key,
            status="success"
        )
        
        result = {
            "order_id": order_id,
            "status": "created",
            "total_amount": total_amount,
            "idempotency_key": idempotency_key
        }
        
        # Store result for idempotency
        await idempotency_handler.store_result(idempotency_key, result)
        
        return result
        
    except Exception as e:
        await db_rate_limiter.record_db_error()
        await TransactionLogDB.log_transaction(
            user_id=current_user,
            product_id=order.items[0].product_id,
            quantity=order.items[0].quantity,
            idempotency_key=idempotency_key,
            status="failed",
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing order"
        )

@app.get("/api/user/orders")
async def user_get_orders(current_user: str = Depends(get_current_user)):
    """User: Get own orders"""
    orders = await OrderDB.get_orders_by_user(current_user)
    return {"orders": orders}

@app.get("/api/user/orders/{order_id}")
async def user_get_order_detail(
    order_id: str,
    current_user: str = Depends(get_current_user)
):
    """User: Get order details"""
    order = await OrderDB.get_order_by_id(order_id)
    
    if not order or order.get("user_id") != current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order

# ===================== HEALTH CHECK =====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "OK", "message": "E-Commerce API is running"}

@app.get("/api/status")
async def api_status():
    """Check database status and product count"""
    try:
        product_count = await db.db["products"].count_documents({})
        user_count = await db.db["users"].count_documents({})
        order_count = await db.db["orders"].count_documents({})
        
        return {
            "status": "OK",
            "database": "Connected",
            "products": product_count,
            "users": user_count,
            "orders": order_count
        }
    except Exception as e:
        return {
            "status": "Error",
            "database": "Disconnected",
            "error": str(e)
        }

# ===================== SEED DATA ENDPOINT =====================

@app.post("/api/admin/seed-excel")
async def admin_seed_excel(current_user: str = Depends(get_current_user)):
    """
    Admin: Seed database from Excel file
    Useful for reloading data or manual trigger
    """
    try:
        # Try multiple possible paths
        possible_paths = [
            "backend/Adidas US Sales Datasets.xlsx",
            "Adidas US Sales Datasets.xlsx",
            "../Adidas US Sales Datasets.xlsx",
            "../../Adidas US Sales Datasets.xlsx",
        ]
        
        excel_path = None
        for path in possible_paths:
            if os.path.exists(path):
                excel_path = path
                break
        
        if not excel_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Excel file not found. Tried: {', '.join(possible_paths)}"
            )
        
        # Load and insert
        products = await load_excel_data(excel_path)
        
        if not products:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No products loaded from Excel"
            )
        
        result = await db.db["products"].insert_many(products)
        
        return {
            "status": "success",
            "products_inserted": len(result.inserted_ids),
            "message": f"Successfully loaded {len(result.inserted_ids)} products from Excel"
        }
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error seeding data: {str(e)}"
        )

# ===================== STATIC FILES ROUTES =====================

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
async def serve_root():
    """Serve login page at root"""
    login_file = os.path.join(frontend_path, "login.html")
    if os.path.exists(login_file):
        return FileResponse(login_file)
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/login")
async def serve_login_root():
    """Serve login page at /login"""
    login_file = os.path.join(frontend_path, "login.html")
    if os.path.exists(login_file):
        return FileResponse(login_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/login.html")
async def serve_login():
    """Serve login page"""
    login_file = os.path.join(frontend_path, "login.html")
    if os.path.exists(login_file):
        return FileResponse(login_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/user-store.html")
async def serve_user_store():
    """Serve user store page"""
    file = os.path.join(frontend_path, "user-store.html")
    if os.path.exists(file):
        return FileResponse(file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/admin-dashboard.html")
async def serve_admin_dashboard():
    """Serve admin dashboard"""
    file = os.path.join(frontend_path, "admin-dashboard.html")
    if os.path.exists(file):
        return FileResponse(file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/provider-panel.html")
async def serve_provider_panel():
    """Serve provider panel"""
    file = os.path.join(frontend_path, "provider-panel.html")
    if os.path.exists(file):
        return FileResponse(file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
