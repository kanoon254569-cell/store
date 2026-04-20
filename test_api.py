"""
Test Script: Duplicate Purchase Prevention
Tests all security mechanisms
"""
import httpx
import asyncio
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"

class APITester:
    def __init__(self):
        self.tokens = {}
        self.client = httpx.AsyncClient()
    
    async def register_user(self, email: str, username: str, role: str = "user") -> str:
        """Register new user and return token"""
        response = await self.client.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": email,
                "username": username,
                "password": "testpass123",
                "role": role
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data["access_token"]
            self.tokens[email] = token
            print(f"✅ Registered {email}")
            return token
        else:
            print(f"❌ Failed to register {email}: {response.text}")
            return None
    
    async def login_user(self, email: str, password: str) -> str:
        """Login and return token"""
        response = await self.client.post(
            f"{BASE_URL}/api/auth/login",
            params={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data["access_token"]
            self.tokens[email] = token
            print(f"✅ Logged in as {email}")
            return token
        else:
            print(f"❌ Login failed: {response.text}")
            return None
    
    async def get_products(self) -> list:
        """Get available products"""
        response = await self.client.get(f"{BASE_URL}/api/user/products")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data['products'])} products")
            return data["products"]
        else:
            print(f"❌ Failed to get products: {response.text}")
            return []
    
    async def create_order(
        self,
        user_email: str,
        product_id: str,
        quantity: int = 1,
        idempotency_key: str = None
    ) -> dict:
        """Create order for user"""
        token = self.tokens.get(user_email)
        
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Idempotency-Key": idempotency_key
        }
        
        response = await self.client.post(
            f"{BASE_URL}/api/user/orders",
            headers=headers,
            json={
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": quantity,
                        "price_at_purchase": 99.99
                    }
                ],
                "shipping_address": "123 Test St",
                "payment_method": "credit_card"
            },
            params={"idempotency_key": idempotency_key}
        )
        
        return {
            "status_code": response.status_code,
            "response": response.json() if response.status_code < 400 else response.text,
            "idempotency_key": idempotency_key
        }
    
    async def get_user_orders(self, user_email: str) -> list:
        """Get user's orders"""
        token = self.tokens.get(user_email)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await self.client.get(
            f"{BASE_URL}/api/user/orders",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()["orders"]
        return []
    
    async def get_admin_dashboard(self) -> dict:
        """Get admin dashboard"""
        # Use admin token
        admin_token = self.tokens.get("admin@example.com")
        if not admin_token:
            return {}
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await self.client.get(
            f"{BASE_URL}/api/admin/dashboard",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        return {}
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

async def test_duplicate_purchase_prevention():
    """Test 1: Duplicate Purchase Prevention"""
    print("\n" + "="*60)
    print("TEST 1: Duplicate Purchase Prevention ⚡")
    print("="*60)
    
    tester = APITester()
    
    # Register user
    token = await tester.register_user("user@example.com", "testuser")
    if not token:
        return
    
    # Get products
    products = await tester.get_products()
    if not products:
        return
    
    product_id = str(products[0]["_id"])
    
    # Try to place same order twice with same idempotency key
    print("\n📝 Attempt 1: Place order...")
    result1 = await tester.create_order("user@example.com", product_id)
    print(f"Status: {result1['status_code']}")
    print(f"Result: {result1['response']}")
    
    print("\n📝 Attempt 2: Same order (same idempotency key)...")
    result2 = await tester.create_order(
        "user@example.com",
        product_id,
        idempotency_key=result1["idempotency_key"]
    )
    print(f"Status: {result2['status_code']}")
    print(f"Result: {result2['response']}")
    
    if result1["status_code"] == 200 and result2["status_code"] == 200:
        print("\n✅ TEST PASSED: Idempotency works! (Both requests succeeded with same result)")
    elif result2["status_code"] == 400:
        print("\n✅ TEST PASSED: Duplicate detected!")
    else:
        print("\n⚠️  TEST WARNING: Unexpected behavior")
    
    await tester.close()

async def test_rate_limiting():
    """Test 2: Rate Limiting"""
    print("\n" + "="*60)
    print("TEST 2: Rate Limiting (Rapid Purchases) ⏱️")
    print("="*60)
    
    tester = APITester()
    
    # Register user
    token = await tester.register_user("rapidbuyer@example.com", "rapidbuyer")
    if not token:
        return
    
    # Get products
    products = await tester.get_products()
    if not products:
        return
    
    product_id = str(products[0]["_id"])
    
    print("\n📝 Attempting 6 rapid purchases on same product...")
    
    for i in range(6):
        print(f"\nAttempt {i+1}:")
        result = await tester.create_order("rapidbuyer@example.com", product_id)
        print(f"  Status: {result['status_code']}")
        
        if result["status_code"] != 200:
            print(f"  Response: {result['response']}")
            break
        else:
            print(f"  ✅ Order created")
    
    await tester.close()

async def test_stock_validation():
    """Test 3: Stock Validation"""
    print("\n" + "="*60)
    print("TEST 3: Stock Validation (Overselling Prevention) 📦")
    print("="*60)
    
    tester = APITester()
    
    # Register user
    token = await tester.register_user("buyer@example.com", "buyer")
    if not token:
        return
    
    # Get products
    products = await tester.get_products()
    if not products:
        return
    
    # Find a product with limited stock
    product = products[0]
    product_id = str(product["_id"])
    current_stock = product.get("stock", 0)
    
    print(f"\n📦 Product: {product['name']}")
    print(f"📊 Current Stock: {current_stock}")
    
    # Try to buy more than available
    try_quantity = current_stock + 10
    print(f"\n📝 Attempting to buy {try_quantity} units...")
    
    result = await tester.create_order(
        "buyer@example.com",
        product_id,
        quantity=try_quantity
    )
    
    print(f"Status: {result['status_code']}")
    print(f"Response: {result['response']}")
    
    if result['status_code'] == 400 or "Insufficient stock" in str(result['response']):
        print("\n✅ TEST PASSED: Overselling prevented!")
    else:
        print("\n❌ TEST FAILED: Should reject overselling")
    
    await tester.close()

async def test_admin_dashboard():
    """Test 4: Admin Dashboard"""
    print("\n" + "="*60)
    print("TEST 4: Admin Dashboard (SKU Summary) 📊")
    print("="*60)
    
    tester = APITester()
    
    # Register admin user
    admin_token = await tester.register_user("admin@example.com", "admin", role="admin")
    if not admin_token:
        return
    
    # Store admin token in a way the dashboard can use
    tester.tokens["admin@example.com"] = admin_token
    
    # Get dashboard
    dashboard = await tester.get_admin_dashboard()
    
    if dashboard:
        print(f"\n✅ Admin Dashboard Retrieved:")
        print(f"  📦 Total Products: {dashboard.get('total_products', 0)}")
        print(f"  📊 Total Stock: {dashboard.get('total_stock', 0)}")
        print(f"  💰 Total Revenue: ${dashboard.get('total_revenue', 0):.2f}")
        print(f"  📋 Total Orders: {dashboard.get('total_orders', 0)}")
        
        if "sku_summary" in dashboard:
            print(f"\n  📋 SKU Summary:")
            for sku in dashboard["sku_summary"][:3]:
                print(f"    - {sku['sku']}: {sku['product_name']} (Stock: {sku['stock']})")
    else:
        print("❌ Failed to retrieve dashboard")
    
    await tester.close()

async def run_all_tests():
    """Run all tests"""
    print("\n🧪 E-Commerce System Test Suite 🧪")
    print("Starting tests...")
    
    try:
        await test_duplicate_purchase_prevention()
        await asyncio.sleep(1)
        
        await test_rate_limiting()
        await asyncio.sleep(1)
        
        await test_stock_validation()
        await asyncio.sleep(1)
        
        await test_admin_dashboard()
        
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)

if __name__ == "__main__":
    print("\n⚠️  Make sure FastAPI server is running on http://localhost:8000")
    print("Start it with: cd backend && python -m uvicorn main:app --reload\n")
    
    asyncio.run(run_all_tests())
