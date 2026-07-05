#!/bin/bash
# AnomalyWatch Quick Start Validation Script

echo "========================================"
echo "AnomalyWatch Quick Start Guide"
echo "========================================"
echo ""

# Check Python version
echo "1. Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1)
echo "   $PYTHON_VERSION"

if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "   ✓ Python version OK"
else
    echo "   ✗ Python 3.10+ required"
    exit 1
fi

echo ""

# Create virtual environment
echo "2. Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✓ Virtual environment created"
else
    echo "   ✓ Virtual environment already exists"
fi

echo ""

# Install dependencies
echo "3. Installing dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r deploy/requirements.txt
echo "   ✓ Dependencies installed"

echo ""

# Create required directories
echo "4. Creating required directories..."
mkdir -p models logs
echo "   ✓ Directories created"

echo ""

# Run application
echo "5. Starting AnomalyWatch..."
echo ""
echo "========================================"
echo "Dashboard will be available at:"
echo "  http://localhost:5000"
echo ""
echo "First run will perform 15-minute baseline learning."
echo "Press Ctrl+C to stop the application."
echo "========================================"
echo ""

python app.py
