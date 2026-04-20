#!/bin/bash

# E-Commerce System Setup Script

echo "🚀 Starting E-Commerce System Setup..."

# Check Python version
python_version=$(python3 --version 2>&1)
echo "✅ Using: $python_version"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📝 Example Commands:"
echo ""
echo "1️⃣  Start FastAPI Server:"
echo "   cd backend && python -m uvicorn main:app --reload --port 8000"
echo ""
echo "2️⃣  Load Excel Data (after MongoDB is running):"
echo "   python backend/data_loader.py '../Adidas US Sales Datasets.xlsx'"
echo ""
echo "3️⃣  API Documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "4️⃣  Stop Server: Press Ctrl+C"
echo ""
