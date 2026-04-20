"""
Export all MongoDB data to Excel
"""
import pandas as pd
from datetime import datetime
import pymongo
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

def export_all_data_to_excel():
    """
    Export all data from MongoDB to Excel file
    Creates multiple sheets for each collection
    """
    try:
        # Get MongoDB connection string
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        database_name = os.getenv("DATABASE_NAME", "ecommerce_db")
        
        # Connect to MongoDB
        client = pymongo.MongoClient(mongodb_url)
        db = client[database_name]
        print(f"✅ Connected to MongoDB: {database_name}")
        
        # Get all collection names
        collections = db.list_collection_names()
        print(f"📋 Found {len(collections)} collections: {collections}")
        
        # Create Excel writer
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"export_data_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            total_records = 0
            
            for collection_name in collections:
                print(f"\n📄 Exporting collection: {collection_name}")
                
                # Get all documents from collection
                documents = list(db[collection_name].find({}))
                
                if not documents:
                    print(f"  ⚠️  No records found")
                    continue
                
                print(f"  📊 Found {len(documents)} records")
                
                # Convert to DataFrame
                df = pd.DataFrame(documents)
                
                # Handle MongoDB ObjectId and datetime objects
                for column in df.columns:
                    try:
                        # Convert ObjectId to string
                        if column == '_id' or df[column].dtype == 'object':
                            df[column] = df[column].astype(str)
                    except Exception as e:
                        print(f"  ⚠️  Error converting column {column}: {str(e)}")
                
                # For datetime columns, convert to string for better Excel compatibility
                for column in df.columns:
                    if 'datetime64' in str(df[column].dtype) or 'at' in column.lower():
                        df[column] = df[column].astype(str)
                
                # Format column names - remove leading/trailing spaces
                df.columns = df.columns.str.strip()
                
                # Clean sheet name (max 31 chars for Excel)
                sheet_name = collection_name[:31]
                
                # Write to Excel
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                total_records += len(documents)
                print(f"  ✅ Exported {len(documents)} records to sheet '{sheet_name}'")
                
                # Auto-adjust column widths
                worksheet = writer.sheets[sheet_name]
                for column in df.columns:
                    max_length = max(
                        df[column].astype(str).apply(len).max(),
                        len(column)
                    )
                    worksheet.column_dimensions[chr(65 + df.columns.get_loc(column))].width = min(max_length + 2, 50)
        
        print(f"\n✅ Export completed successfully!")
        print(f"📁 File saved: {output_file}")
        print(f"📊 Total records exported: {total_records}")
        
        # Close MongoDB connection
        client.close()
        print("✅ Disconnected from MongoDB")
        
        return output_file
    
    except Exception as e:
        print(f"❌ Error during export: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Run the export
    result = export_all_data_to_excel()
    
    if result:
        print(f"\n🎉 Data successfully exported to: {result}")
    else:
        print("\n❌ Export failed!")
        sys.exit(1)
