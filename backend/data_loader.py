

"""
Excel Data Loader
Load product data from Adidas Sales Dataset into MongoDB
"""
import pandas as pd
from typing import List, Dict
from datetime import datetime
import asyncio

async def load_excel_data(excel_path: str):
    """
    Load Excel data and prepare for MongoDB
    Flexible column detection for different Excel formats
    """
    try:
        # Try reading with different approaches
        print(f"✅ Loading Excel file: {excel_path}")
        
        # First, try to read all sheets
        xls = pd.ExcelFile(excel_path)
        print(f"📋 Available sheets: {xls.sheet_names}")
        
        # Read the first sheet
        sheet_name = xls.sheet_names[0]
        print(f"📄 Reading sheet: {sheet_name}")
        
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
        print(f"📊 Initial shape (no header): {df.shape}")
        
        # Try to find header row (first row with actual data)
        # Look for rows that might contain typical column names
        header_row = 0
        for idx in range(min(5, len(df))):
            row_values = df.iloc[idx].astype(str).values
            # Check if this looks like a header row
            if any('Retailer' in str(v) or 'Product' in str(v) or 'Price' in str(v) for v in row_values):
                header_row = idx
                print(f"🎯 Found header at row {idx}")
                break
        
        # Re-read with proper header
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
        print(f"📊 Columns found: {list(df.columns)}")
        print(f"📈 Rows: {len(df)}")
        
        # Clean up column names - remove leading/trailing whitespace
        df.columns = df.columns.str.strip()
        
        # Try to find the right columns regardless of exact names
        # Map common variations to standard names
        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'product' in col_lower:
                column_mapping[col] = 'Product'
            elif 'price' in col_lower and 'unit' in col_lower:
                column_mapping[col] = 'Price per Unit'
            elif 'unit' in col_lower and ('sold' in col_lower or 'sales' in col_lower):
                column_mapping[col] = 'Units Sold'
            elif 'retailer' in col_lower or 'store' in col_lower:
                column_mapping[col] = 'Retailer'
        
        # Rename columns
        if column_mapping:
            df = df.rename(columns=column_mapping)
            print(f"🔄 Remapped columns: {column_mapping}")
        
        # Check if we have the required columns
        required_cols = ['Product', 'Price per Unit', 'Units Sold']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"⚠️  Missing columns: {missing_cols}")
            print(f"📊 Available columns: {list(df.columns)}")
            # If we're missing product column, just use index
            if 'Product' not in df.columns and len(df.columns) > 0:
                # Use first column as product name
                df['Product'] = df.iloc[:, 0].astype(str)
            if 'Price per Unit' not in df.columns and len(df.columns) > 1:
                df['Price per Unit'] = pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(10.0)
            if 'Units Sold' not in df.columns and len(df.columns) > 2:
                df['Units Sold'] = pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(1).astype(int)
        
        # Transform to products
        products = []
        
        # Create unique SKUs from data
        if 'Product' in df.columns:
            df = df.dropna(subset=['Product'])
            
            # Group by product
            if len(df) > 0:
                grouped = df.groupby(['Product']).agg({
                    'Price per Unit': 'first',
                    'Units Sold': 'sum',
                }).reset_index()
                
                for idx, row in grouped.iterrows():
                    try:
                        product_name = str(row['Product']).strip()
                        if product_name and product_name != 'nan':
                            product = {
                                "name": product_name,
                                "sku": f"SKU-{product_name.replace(' ', '-')[:20].upper()}-{idx:04d}",
                                "price": float(pd.to_numeric(row['Price per Unit'], errors='coerce') or 10.0),
                                "stock": int(pd.to_numeric(row['Units Sold'], errors='coerce') or 1) * 2,
                                "category": "Footwear",
                                "description": f"{product_name} - Product from Adidas dataset",
                                "provider_id": "provider_001",
                                "created_at": datetime.utcnow(),
                                "updated_at": datetime.utcnow(),
                                "stock_history": []
                            }
                            products.append(product)
                    except Exception as e:
                        print(f"⚠️  Skipping row {idx}: {str(e)}")
                        continue
        
        print(f"✅ Created {len(products)} products")
        return products
    
    except Exception as e:
        print(f"❌ Error loading Excel: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def seed_database(excel_path: str, db):
    """
    Load Excel data and insert into MongoDB
    """
    products = await load_excel_data(excel_path)
    
    if products:
        try:
            result = await db.db["products"].insert_many(products)
            print(f"✅ Inserted {len(result.inserted_ids)} products into MongoDB")
            return result.inserted_ids
        except Exception as e:
            print(f"❌ Error inserting to DB: {str(e)}")
            return []
    else:
        print("❌ No products to insert")
        return []

# Example usage in main.py
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
        products = asyncio.run(load_excel_data(excel_path))
        print(f"\n📦 Sample products ({len(products)} total):")
        for p in products[:5]:
            print(f"  - {p['name']} (SKU: {p['sku']}, Stock: {p['stock']}, Price: {p['price']})")

