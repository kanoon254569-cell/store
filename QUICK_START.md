# 🚀 QUICK START GUIDE

ระบบขายออนไลน์ครบวงจรพร้อมใช้งาน (FastAPI + MongoDB + Multi-User)

## 📋 ขั้นตอนการเริ่มต้น

### 1️⃣ Install Dependencies

```bash
# Navigate to project directory
cd /Volumes/ketamine2jai/งาน/Web_Data/ecommerce-system

# Run setup script (first time only)
chmod +x setup.sh
./setup.sh

# Or manually install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2️⃣ Start MongoDB (Choose One Method)

#### Method A: Using Docker Compose (Easiest)
```bash
# Start both MongoDB and FastAPI together
docker-compose up -d

# Check status
docker-compose ps

# Stop
docker-compose down
```

#### Method B: Local MongoDB
```bash
# Terminal 1: Start MongoDB
mongod --dbpath /path/to/mongodb/data

# If you don't have MongoDB installed
# macOS: brew install mongodb-community
# Ubuntu: sudo apt-get install mongodb
# Or use Docker: docker run -p 27017:27017 mongo:latest
```

### 3️⃣ Setup .env File

```bash
cp .env.example .env

# Edit .env if needed (usually works as-is)
cat .env
```

### 4️⃣ Start FastAPI Server

```bash
# Terminal 2: Start FastAPI
cd backend
python -m uvicorn main:app --reload --port 8000

# You'll see:
# ✅ Connected to MongoDB: ecommerce_db
# Uvicorn running on http://localhost:8000
```

### 5️⃣ Load Excel Data (Optional)

```bash
# Terminal 3: Load sample data
cd backend
python data_loader.py '../Adidas US Sales Datasets.xlsx'

# Output:
# ✅ Loaded Excel file: ../Adidas US Sales Datasets.xlsx
# ✅ Inserted XXX products into MongoDB
```

---

## 🔗 Access Points

| Type | URL | Role |
|------|-----|------|
| **Login/Register** | http://localhost:8000/frontend/login.html | All |
| **API Docs** | http://localhost:8000/docs | Developer |
| **Redoc** | http://localhost:8000/redoc | Developer |
| **Health Check** | http://localhost:8000/health | All |

---

## 👥 Test Accounts

After registration, accounts are automatically created:

```
Admin:
  Email: admin@example.com
  Password: testpass123
  Role: admin
  → Access: /admin-dashboard.html

Provider:
  Email: provider@example.com
  Password: testpass123
  Role: provider
  → Access: /provider-panel.html

User (Customer):
  Email: user@example.com
  Password: testpass123
  Role: user
  → Access: /user-store.html
```

---

## 🧪 Test the System

### Option A: Use Web Frontends

1. Open http://localhost:8000/frontend/login.html
2. Register new accounts (create test accounts)
3. Test each interface:
   - **Admin**: View SKU summary, sales overview
   - **Provider**: Add products, manage stock
   - **User**: Browse and buy products

### Option B: Run Automated Tests

```bash
# Terminal 3: Run test suite
python test_api.py

# Tests cover:
# ✓ Duplicate purchase prevention
# ✓ Rate limiting
# ✓ Stock validation
# ✓ Admin dashboard
```

### Option C: Use curl (API Testing)

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123",
    "role": "user"
  }'

# Login
curl -X POST "http://localhost:8000/api/auth/login?email=test@example.com&password=password123"

# Get token from response, then use it for protected routes
# GET products
curl http://localhost:8000/api/user/products

# Place order (with protection)
curl -X POST http://localhost:8000/api/user/orders \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [{
      "product_id": "...",
      "quantity": 1,
      "price_at_purchase": 99.99
    }],
    "shipping_address": "123 Test St",
    "payment_method": "credit_card"
  }'
```

---

## 📊 Features Overview

### ✅ Admin Panel
- SKU summary (รวมสต็อกทั้งหมด)
- Sales overview (ยอดขายแบบรายวัน)
- Inventory alerts
- Real-time dashboard

### ✅ Provider Panel
- Add new products
- Manage stock/restock
- View personal dashboard
- Track own orders

### ✅ User Store
- Browse products by category
- Search functionality
- Shopping cart
- Secure checkout with idempotency

### ✅ Security Features

#### 1. **Duplicate Purchase Prevention** 🛡️
- Idempotency keys
- Transaction logging
- 1-minute purchase cooldown per product

#### 2. **Stock Validation** 📦
- No overselling allowed
- Real-time stock checks
- Automatic deduction

#### 3. **Rate Limiting** ⚡
- 60 req/min per user
- Circuit breaker for DB
- Prevents flooding

#### 4. **Database Protection** 💾
- Connection pooling
- Error monitoring
- Auto-recovery

---

## 📂 Project Structure

```
ecommerce-system/
├── backend/
│   ├── main.py                # FastAPI server
│   ├── models.py              # Data models
│   ├── database.py            # DB operations
│   ├── security.py            # Auth & protection
│   ├── config.py              # Configuration
│   └── data_loader.py         # Excel importer
├── frontend/
│   ├── login.html             # Login/Register
│   ├── admin-dashboard.html   # Admin panel
│   ├── provider-panel.html    # Provider panel
│   └── user-store.html        # User storefront
├── requirements.txt           # Python packages
├── docker-compose.yml         # Docker setup
├── Dockerfile                 # API container
├── .env.example              # Template config
├── test_api.py               # Test suite
├── setup.sh                  # Setup script
├── README.md                 # Full documentation
└── QUICK_START.md           # This file
```

---

## 🔧 Troubleshooting

### ❌ "Connection refused" to MongoDB
```bash
# Check if MongoDB is running
ps aux | grep mongod

# If not running, start it:
mongod --dbpath ~/mongodb/data

# Or use Docker:
docker run -p 27017:27017 mongo:latest
```

### ❌ "Port 8000 already in use"
```bash
# Kill existing process
lsof -i :8000
kill -9 <PID>

# Or use different port
python -m uvicorn backend.main:app --port 8001
```

### ❌ "Module not found"
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt
```

### ❌ "CORS error in frontend"
```bash
# CORS is already configured in main.py
# If still having issues, check:
# 1. API is running on port 8000
# 2. Browser console for actual error
# 3. Make sure using http:// not https://
```

### ❌ "Excel file not loading"
```bash
# Check file path
ls -la ../Adidas\ US\ Sales\ Datasets.xlsx

# If not found, adjust path in command
python data_loader.py '/full/path/to/file.xlsx'
```

---

## 🛑 Stop Everything

```bash
# Stop FastAPI (Ctrl+C in terminal)

# Stop MongoDB (Ctrl+C)

# If using Docker Compose:
docker-compose down

# Deactivate venv
deactivate
```

---

## 📈 Next Steps

1. **Customize Frontend** - Edit HTML files for your branding
2. **Add Payment Gateway** - Integrate Stripe/PayPal
3. **Setup Notifications** - Add email/SMS alerts
4. **Deploy to Cloud** - Use AWS/Heroku/Railway
5. **Add Analytics** - Track sales and user behavior
6. **Mobile App** - Create React Native version

---

## 🆘 Getting Help

- **API Documentation**: http://localhost:8000/docs
- **Full README**: See README.md
- **Check Logs**: Look at terminal output for errors
- **Test Suite**: Run `test_api.py` to verify setup

---

## ✅ Verification Checklist

- [ ] Virtual environment activated
- [ ] All dependencies installed
- [ ] MongoDB running and accessible
- [ ] .env file created
- [ ] FastAPI server running (port 8000)
- [ ] Can access http://localhost:8000/health ✅
- [ ] Can access http://localhost:8000/docs
- [ ] Can register and login
- [ ] Can browse products
- [ ] Can place orders

---

**System Status**: ✅ Ready for local testing!

Good luck! 🎉
