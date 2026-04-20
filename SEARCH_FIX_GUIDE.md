# 🔍 Product Search Fix Guide

## 🐛 Problem Identified

The product search in Excel was not working because:

1. **No Data in Database**: The Excel file (`Adidas US Sales Datasets.xlsx`) exists but was never loaded into MongoDB
2. **Missing Seed Process**: There was no automatic or manual way to load Excel data into the database on application startup
3. **Empty Search Results**: When users searched, the frontend found no products because the database was empty

## ✅ Solution Implemented

### 1. **Automatic Data Loading on Startup**
- Modified the `lifespan()` function in `backend/main.py`
- Now automatically loads Excel data when the app starts (if database is empty)
- Displays status messages in the console

### 2. **Manual Seed Endpoint**
- Added `/api/admin/seed-excel` endpoint (POST)
- Allows manual reloading of products from Excel
- Requires authentication (admin only)

### 3. **Backend Search Endpoint**
- Added `/api/user/search` endpoint (GET)
- Supports searching by product name, SKU, or description
- Much more efficient than client-side search for large datasets
- Parameters: `q` (search query), `category` (filter by category)

### 4. **Database Status Endpoint**
- Added `/api/status` endpoint (GET)
- Check database connection and product count
- Useful for debugging

## 🚀 How to Use

### Method 1: Automatic Loading (Recommended)
```bash
# Just start the app - Excel data loads automatically!
python -m uvicorn backend.main:app --reload
# OR
docker-compose up
```

### Method 2: Manual Seeding
```bash
# After app is running, make a POST request:
curl -X POST http://localhost:8000/api/admin/seed-excel \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Method 3: Check Status
```bash
# Check if products are loaded:
curl http://localhost:8000/api/status
```

**Response example:**
```json
{
  "status": "OK",
  "database": "Connected",
  "products": 50,
  "users": 5,
  "orders": 2
}
```

## 🔎 How to Search Products

### Frontend (Client-side)
Users can search in the UI as before - it now works because products are loaded!

### Backend (Server-side)
```bash
# Search by product name
GET /api/user/search?q=air max

# Search with category filter
GET /api/user/search?q=soccer&category=Footwear

# Get all products in a category
GET /api/user/products?category=Footwear
```

**Response example:**
```json
{
  "query": "air max",
  "category": null,
  "count": 3,
  "products": [
    {
      "_id": "...",
      "name": "Nike Air Max",
      "sku": "SKU-NIKE-AIR-MAX-0001",
      "price": 129.99,
      "stock": 50,
      "category": "Footwear"
    }
  ]
}
```

## 📁 File Locations

- **Excel File**: `/Volumes/ketamine2jai/งาน/Web_Data/Adidas US Sales Datasets.xlsx`
- **Data Loader**: `backend/data_loader.py`
- **API Routes**: `backend/main.py`
- **Frontend Search**: `frontend/user-store.html`

## 🛠️ Troubleshooting

### "No products found"
1. Check `/api/status` - if `products: 0`, data isn't loaded
2. Check console output for any Excel loading errors
3. Make sure Excel file path is correct
4. Manually trigger: `POST /api/admin/seed-excel`

### "Excel file not found"
- Excel file must be at: `../Adidas US Sales Datasets.xlsx` (relative to backend/)
- Currently at: `/Volumes/ketamine2jai/งาน/Web_Data/Adidas US Sales Datasets.xlsx`
- Adjust path in `backend/main.py` if needed

### Search returns empty
- Verify products are loaded: `GET /api/status`
- Try backend search: `GET /api/user/search?q=*` or `GET /api/user/products`
- Check MongoDB is running and connected

## 📊 Database Collections

Products are stored in MongoDB with structure:
```json
{
  "_id": "ObjectId",
  "name": "Product Name",
  "sku": "SKU-UNIQUE-CODE",
  "price": 129.99,
  "stock": 50,
  "category": "Footwear",
  "description": "...",
  "provider_id": "provider_001",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "stock_history": []
}
```

## 📈 Key Changes Made

1. **backend/main.py**
   - Added data_loader imports
   - Modified lifespan() for auto-loading
   - Added `/api/admin/seed-excel` endpoint
   - Added `/api/user/search` endpoint
   - Added `/api/status` endpoint

2. **backend/data_loader.py**
   - Already had Excel loading logic, just needed to be called

3. **frontend/user-store.html**
   - Search still works as before (client-side filtering)
   - Can optionally be updated to use backend search for better performance

## ✨ Next Steps (Optional Improvements)

1. Update frontend to use backend search endpoint for large datasets
2. Add pagination to search results
3. Add sorting options (by price, name, stock)
4. Add caching for frequently searched terms
5. Add product filters (price range, stock status, etc.)

---

**Summary**: Excel products now automatically load when the app starts. Search works instantly! 🎉
