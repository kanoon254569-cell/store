"""Security & Rate Limiting"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPBasicCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from .config import settings
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from functools import wraps
from typing import Optional, Dict
import asyncio
from collections import defaultdict

# ===================== JWT & AUTHENTICATION =====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

security = HTTPBearer()

async def get_current_user(credentials = Depends(security)):
    """Get current user from token"""
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return user_id

# ===================== RATE LIMITING =====================

class DuplicatePurchasePreventionRate:
    """
    ป้องกันการซื้อซ้ำ (Duplicate Purchase Protection)
    
    Mechanism:
    1. ใช้ idempotency_key เหมือนกันไม่ว่า request จะมากี่ครั้ง = result เหมือนเดิม
    2. ตรวจสอบว่า user ซื้อสินค้าเดียวกันในเวลา short window ไม่ได้
    3. Log ทุกครั้งที่มี purchase attempt
    """
    
    def __init__(self):
        self.purchase_attempts: Dict[str, list] = defaultdict()  # user_id -> [(timestamp, product_id)]
        self.lock = asyncio.Lock()
    
    async def check_purchase_rate(self, user_id: str, product_id: str) -> bool:
        """
        Check if user is trying to purchase same product too quickly
        Returns: True if allowed, False if rate limited
        """
        async with self.lock:
            now = datetime.utcnow()
            
            # Initialize user attempts if not exists
            if user_id not in self.purchase_attempts:
                self.purchase_attempts[user_id] = []
            
            # Remove old attempts (outside 1 minute window)
            window_start = now - timedelta(minutes=1)
            self.purchase_attempts[user_id] = [
                (ts, pid) for ts, pid in self.purchase_attempts[user_id]
                if ts > window_start
            ]
            
            # Check if same product purchased in this window
            same_product_attempts = [
                (ts, pid) for ts, pid in self.purchase_attempts[user_id]
                if pid == product_id
            ]
            
            if len(same_product_attempts) >= settings.PURCHASE_LIMIT_PER_MINUTE:
                return False
            
            # Check total purchase rate
            if len(self.purchase_attempts[user_id]) >= settings.REQUESTS_PER_MINUTE * 5:
                return False
            
            # Add new attempt
            self.purchase_attempts[user_id].append((now, product_id))
            return True

duplicate_prevention = DuplicatePurchasePreventionRate()

# ===================== REQUEST FLOODING PROTECTION (DB Level) =====================

class DatabaseRateLimiter:
    """
    ป้องกัน Request Flooding ที่อาจทำ Database ล้ม
    
    Strategies:
    1. Limit connections per IP
    2. Limit queries per user per minute
    3. Queue long-running queries
    4. Implement circuit breaker for DB
    """
    
    def __init__(self):
        self.user_requests: Dict[str, list] = defaultdict(list)
        self.lock = asyncio.Lock()
        self.circuit_breaker_open = False
        self.circuit_breaker_errors = 0
    
    async def check_user_rate(self, user_id: str) -> bool:
        """Check if user exceeded rate limit"""
        async with self.lock:
            now = datetime.utcnow()
            minute_ago = now - timedelta(minutes=1)
            
            # Remove old requests
            self.user_requests[user_id] = [
                ts for ts in self.user_requests[user_id]
                if ts > minute_ago
            ]
            
            # Check limit
            if len(self.user_requests[user_id]) >= settings.REQUESTS_PER_MINUTE:
                return False
            
            self.user_requests[user_id].append(now)
            return True
    
    async def check_circuit_breaker(self):
        """Check if circuit breaker is open"""
        if self.circuit_breaker_open:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - database circuit breaker is open"
            )
    
    async def record_db_error(self):
        """Record database error for circuit breaker"""
        async with self.lock:
            self.circuit_breaker_errors += 1
            if self.circuit_breaker_errors >= 5:
                self.circuit_breaker_open = True
                await asyncio.sleep(30)  # Wait 30 seconds
                self.circuit_breaker_open = False
                self.circuit_breaker_errors = 0

db_rate_limiter = DatabaseRateLimiter()

# ===================== STOCK VALIDATION =====================

async def validate_stock_availability(product_id: str, requested_quantity: int) -> bool:
    """
    Validate if product has enough stock
    This prevents overselling
    """
    from database import ProductDB
    
    product = await ProductDB.get_product_by_id(product_id)
    
    if not product:
        return False
    
    if product.get("stock", 0) < requested_quantity:
        return False
    
    return True

# ===================== IDEMPOTENCY KEY HANDLER =====================

class IdempotencyKeyHandler:
    """
    Handle idempotency keys to prevent duplicate requests
    """
    
    def __init__(self):
        self.processed_keys: Dict[str, Dict] = {}
        self.lock = asyncio.Lock()
    
    async def store_result(self, key: str, result: dict, ttl_seconds: int = 3600):
        """Store result for idempotency key"""
        async with self.lock:
            self.processed_keys[key] = {
                "result": result,
                "timestamp": datetime.utcnow(),
                "ttl": ttl_seconds
            }
    
    async def get_result(self, key: str) -> Optional[dict]:
        """Get stored result if key exists and not expired"""
        async with self.lock:
            if key not in self.processed_keys:
                return None
            
            stored = self.processed_keys[key]
            age = (datetime.utcnow() - stored["timestamp"]).total_seconds()
            
            if age > stored["ttl"]:
                del self.processed_keys[key]
                return None
            
            return stored["result"]
    
    async def cleanup_expired(self):
        """Clean up expired keys (can be called periodically)"""
        async with self.lock:
            now = datetime.utcnow()
            expired_keys = [
                k for k, v in self.processed_keys.items()
                if (now - v["timestamp"]).total_seconds() > v["ttl"]
            ]
            for key in expired_keys:
                del self.processed_keys[key]

idempotency_handler = IdempotencyKeyHandler()
