"""
Create Admin User for E-Commerce System
"""
import asyncio
import pymongo
from datetime import datetime
import bcrypt
from dotenv import load_dotenv
import os

load_dotenv()

async def create_admin_user():
    """Create admin user in database"""
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        database_name = os.getenv("DATABASE_NAME", "ecommerce_db")
        
        client = pymongo.MongoClient(mongodb_url)
        db = client[database_name]
        
        print("✅ Connected to MongoDB")
        
        # Admin credentials
        admin_email = "admin@ecommerce.local"
        admin_username = "admin"
        admin_password = "Admin@123456"
        
        # Check if admin already exists
        existing = db["users"].find_one({"email": admin_email})
        if existing:
            print(f"⚠️  Admin user already exists: {admin_email}")
            print(f"   User ID: {existing['_id']}")
            client.close()
            return
        
        # Hash password
        hashed_pw = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt())
        
        # Create admin user
        admin_user = {
            "email": admin_email,
            "username": admin_username,
            "password_hash": hashed_pw.decode(),
            "role": "admin",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db["users"].insert_one(admin_user)
        
        print("✅ Admin user created successfully!")
        print()
        print("=" * 60)
        print("🔐 ADMIN CREDENTIALS")
        print("=" * 60)
        print(f"Email:    {admin_email}")
        print(f"Password: {admin_password}")
        print(f"Role:     admin")
        print(f"User ID:  {result.inserted_id}")
        print("=" * 60)
        print()
        print("📍 Admin URLs:")
        print("   Login Page:      http://localhost:8001/login")
        print("   Admin Dashboard: http://localhost:8001/admin-dashboard.html")
        print()
        print("📖 API Documentation:")
        print("   Swagger UI: http://localhost:8001/docs")
        print()
        
        # Create provider user too
        provider_email = "provider@ecommerce.local"
        provider_username = "provider"
        provider_password = "Provider@123456"
        
        existing_provider = db["users"].find_one({"email": provider_email})
        if not existing_provider:
            hashed_pw_provider = bcrypt.hashpw(provider_password.encode(), bcrypt.gensalt())
            
            provider_user = {
                "email": provider_email,
                "username": provider_username,
                "password_hash": hashed_pw_provider.decode(),
                "role": "provider",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result_provider = db["users"].insert_one(provider_user)
            
            print("✅ Provider user created successfully!")
            print()
            print("=" * 60)
            print("🏪 PROVIDER CREDENTIALS")
            print("=" * 60)
            print(f"Email:    {provider_email}")
            print(f"Password: {provider_password}")
            print(f"Role:     provider")
            print(f"User ID:  {result_provider.inserted_id}")
            print("=" * 60)
            print()
            print("📍 Provider URLs:")
            print("   Login Page:      http://localhost:8001/login")
            print("   Provider Panel:  http://localhost:8001/provider-panel.html")
            print()
        else:
            print("ℹ️  Provider user already exists")
        
        # Create regular user too
        user_email = "user@ecommerce.local"
        user_username = "user"
        user_password = "User@123456"
        
        existing_user = db["users"].find_one({"email": user_email})
        if not existing_user:
            hashed_pw_user = bcrypt.hashpw(user_password.encode(), bcrypt.gensalt())
            
            regular_user = {
                "email": user_email,
                "username": user_username,
                "password_hash": hashed_pw_user.decode(),
                "role": "user",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result_user = db["users"].insert_one(regular_user)
            
            print("✅ Regular user created successfully!")
            print()
            print("=" * 60)
            print("👤 USER CREDENTIALS")
            print("=" * 60)
            print(f"Email:    {user_email}")
            print(f"Password: {user_password}")
            print(f"Role:     user")
            print(f"User ID:  {result_user.inserted_id}")
            print("=" * 60)
            print()
            print("📍 User URLs:")
            print("   Login Page: http://localhost:8001/login")
            print("   User Store: http://localhost:8001/user-store.html")
            print()
        else:
            print("ℹ️  Regular user already exists")
        
        client.close()
        print("✅ All set! You can now login to the system.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_admin_user())
