"""
Complete Data Pipeline: Load Excel -> MongoDB -> Export Excel
"""
import pandas as pd
from datetime import datetime
import pymongo
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Load environment variables
load_dotenv()

def find_excel_file():
    """Find the Adidas Excel file"""
    possible_paths = [
        "backend/Adidas US Sales Datasets.xlsx",
        "Adidas US Sales Datasets.xlsx",
        "./backend/Adidas US Sales Datasets.xlsx",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Found: {path}")
            return path
    
    print(f"❌ Excel file not found")
    return None

def load_excel_to_mongodb(excel_path):
    """Load Excel data into MongoDB"""
    try:
        print(f"\n📥 Loading data from Excel: {excel_path}")
        
        # Read Excel file with proper header row
        df = pd.read_excel(excel_path, sheet_name=0, header=4)
        print(f"📊 Shape: {df.shape}")
        print(f"📋 Columns: {list(df.columns)}")
        
        # Get MongoDB connection
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        database_name = os.getenv("DATABASE_NAME", "ecommerce_db")
        client = pymongo.MongoClient(mongodb_url)
        db = client[database_name]
        
        print(f"✅ Connected to MongoDB: {database_name}")
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Extract products data
        all_products = []
        
        print(f"\n📄 Processing data...")
        
        # Filter valid rows
        df_clean = df.dropna(subset=['Product']).copy()
        print(f"   📊 Found {len(df_clean)} rows with Product data")
        
        # Group by product to avoid duplicates
        product_dict = {}
        
        for idx, row in df_clean.iterrows():
            try:
                product_name = str(row.get('Product', f"Product {idx}")).strip()
                
                if product_name and product_name != 'nan' and product_name != '':
                    # Use product name as key to aggregate
                    if product_name not in product_dict:
                        price = float(pd.to_numeric(row.get('Price per Unit', 10.0), errors='coerce') or 10.0)
                        units_sold = int(pd.to_numeric(row.get('Units Sold', 1), errors='coerce') or 1)
                        retailer = str(row.get('Retailer', 'Unknown')).strip()
                        
                        product_dict[product_name] = {
                            "name": product_name,
                            "sku": f"SKU-{product_name.replace(' ', '-')[:20].upper()}",
                            "price": price,
                            "stock": units_sold * 2,
                            "category": "Footwear",
                            "description": f"{product_name} - {retailer}",
                            "provider_id": "provider_001",
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                            "stock_history": [],
                            "retailer": retailer
                        }
                    else:
                        # Aggregate stock
                        units_sold = int(pd.to_numeric(row.get('Units Sold', 1), errors='coerce') or 1)
                        product_dict[product_name]["stock"] += units_sold * 2
            except Exception as e:
                print(f"   ⚠️  Skipping row {idx}: {str(e)}")
                continue
        
        all_products = list(product_dict.values())
        print(f"   ✅ Extracted {len(all_products)} unique products")
        
        # Insert into MongoDB
        if all_products:
            try:
                # Clear existing products
                existing = db["products"].count_documents({})
                if existing > 0:
                    print(f"\n🗑️  Clearing {existing} existing products...")
                    db["products"].delete_many({})
                
                # Also insert the raw sales data as another collection
                print(f"\n📝 Saving raw sales data...")
                sales_records = df_clean.to_dict('records')
                for record in sales_records:
                    # Convert datetime objects to strings
                    for key, value in record.items():
                        if pd.api.types.is_datetime64_any_dtype(type(value)):
                            record[key] = str(value)
                
                result_products = db["products"].insert_many(all_products)
                print(f"✅ Inserted {len(result_products.inserted_ids)} products")
                
                result_sales = db["sales"].insert_many(sales_records)
                print(f"✅ Inserted {len(result_sales.inserted_ids)} sales records")
                
            except Exception as e:
                print(f"❌ Error inserting to MongoDB: {str(e)}")
                client.close()
                return False
        else:
            print(f"⚠️  No products extracted from Excel")
        
        client.close()
        return True
    
    except Exception as e:
        print(f"❌ Error loading Excel: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def export_mongodb_to_excel():
    """Export all MongoDB data to Excel"""
    try:
        print(f"\n📤 Exporting data from MongoDB...")
        
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        database_name = os.getenv("DATABASE_NAME", "ecommerce_db")
        
        client = pymongo.MongoClient(mongodb_url)
        db = client[database_name]
        print(f"✅ Connected to MongoDB: {database_name}")
        
        # Get all collections
        collections = db.list_collection_names()
        print(f"📋 Found {len(collections)} collections: {collections}")
        
        if not collections:
            print("⚠️  No collections found in database")
            client.close()
            return None
        
        # Create Excel writer
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"export_all_data_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            total_records = 0
            
            for collection_name in collections:
                print(f"\n📄 Exporting collection: {collection_name}")
                
                # Get all documents
                documents = list(db[collection_name].find({}))
                
                if not documents:
                    print(f"  ⚠️  No records found")
                    continue
                
                print(f"  📊 Found {len(documents)} records")
                
                # Convert to DataFrame
                df = pd.DataFrame(documents)
                
                # Convert ObjectId and datetime to strings
                for column in df.columns:
                    try:
                        if column == '_id' or df[column].dtype == 'object':
                            df[column] = df[column].astype(str)
                    except:
                        pass
                
                for column in df.columns:
                    if 'datetime64' in str(df[column].dtype) or 'at' in column.lower():
                        df[column] = df[column].astype(str)
                
                # Clean column names
                df.columns = df.columns.str.strip()
                
                # Excel sheet name limit (31 chars)
                sheet_name = collection_name[:31]
                
                # Write to Excel
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                total_records += len(documents)
                print(f"  ✅ Exported {len(documents)} records")
                
                # Auto-adjust column widths
                worksheet = writer.sheets[sheet_name]
                for i, column in enumerate(df.columns):
                    max_length = max(
                        df[column].astype(str).apply(len).max(),
                        len(column)
                    )
                    col_letter = chr(65 + i)
                    worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
        
        print(f"\n✅ Export completed!")
        print(f"📁 File saved: {output_file}")
        print(f"📊 Total records exported: {total_records}")
        
        client.close()
        return output_file
    
    except Exception as e:
        print(f"❌ Error during export: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("📊 DATA PIPELINE: Load Excel -> MongoDB -> Export Excel")
    print("=" * 60)
    
    # Step 1: Find Excel file
    excel_file = find_excel_file()
    if not excel_file:
        print("\n❌ Cannot proceed without source Excel file")
        sys.exit(1)
    
    # Step 2: Load to MongoDB
    if not load_excel_to_mongodb(excel_file):
        print("\n❌ Failed to load data to MongoDB")
        sys.exit(1)
    
    # Step 3: Export from MongoDB
    output_file = export_mongodb_to_excel()
    if output_file:
        print(f"\n" + "=" * 60)
        print(f"🎉 SUCCESS! Data exported to: {output_file}")
        print("=" * 60)
    else:
        print("\n❌ Failed to export data from MongoDB")
        sys.exit(1)
