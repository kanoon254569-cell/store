#!/usr/bin/env python3
"""
Quick test script to verify the search fix is working
Run this after the FastAPI server is running
"""

import requests
import json

API_BASE = "http://localhost:8000"

def print_section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")

def test_status():
    """Check database status"""
    print_section("1️⃣  Database Status Check")
    try:
        response = requests.get(f"{API_BASE}/api/status")
        data = response.json()
        print(json.dumps(data, indent=2))
        
        if data.get("products", 0) > 0:
            print(f"\n✅ SUCCESS: {data['products']} products found in database!")
            return True
        else:
            print("\n⚠️  WARNING: No products in database yet")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_browse_all():
    """Browse all products"""
    print_section("2️⃣  Browse All Products")
    try:
        response = requests.get(f"{API_BASE}/api/user/products")
        data = response.json()
        
        products = data.get("products", [])
        print(f"Found {len(products)} products\n")
        
        if products:
            print("Sample products:")
            for p in products[:3]:
                print(f"  - {p.get('name')} (SKU: {p.get('sku')}, Price: ${p.get('price')})")
            return True
        else:
            print("No products available")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_search():
    """Test backend search"""
    print_section("3️⃣  Search Products (Backend Search)")
    
    test_queries = ["air", "soccer", "women"]
    
    for query in test_queries:
        try:
            response = requests.get(f"{API_BASE}/api/user/search", params={"q": query})
            data = response.json()
            
            count = data.get("count", 0)
            print(f"Query: '{query}' → Found {count} products")
            
            if count > 0:
                for p in data.get("products", [])[:2]:
                    print(f"    ✓ {p.get('name')} - ${p.get('price')}")
            print()
        except Exception as e:
            print(f"❌ ERROR searching for '{query}': {e}\n")

def test_category_filter():
    """Test category filter"""
    print_section("4️⃣  Filter by Category")
    try:
        response = requests.get(f"{API_BASE}/api/user/products", params={"category": "Footwear"})
        data = response.json()
        
        products = data.get("products", [])
        print(f"Found {len(products)} products in 'Footwear' category")
        
        if products:
            for p in products[:2]:
                print(f"  - {p.get('name')} (${p.get('price')}, Stock: {p.get('stock')})")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def main():
    print("\n" + "🔍 E-Commerce Product Search Test Script".center(60, "="))
    
    try:
        # Test status
        has_products = test_status()
        
        if not has_products:
            print("\n⚠️  No products in database!")
            print("The app will auto-load on startup, or you can manually trigger:")
            print("   POST /api/admin/seed-excel (requires authentication)")
            return
        
        # Run other tests
        test_browse_all()
        test_search()
        test_category_filter()
        
        print_section("✅ All Tests Complete!")
        print("If all tests passed, search functionality is working correctly!\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ FATAL ERROR: Cannot connect to API")
        print(f"   Make sure the server is running at {API_BASE}")
        print("   Start with: python -m uvicorn backend.main:app --reload")

if __name__ == "__main__":
    main()
