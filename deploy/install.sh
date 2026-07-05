#!/bin/bash
# AnomalyWatch Installation Script for Ubuntu 24.04

set -e

echo "========================================"
echo "AnomalyWatch Installation"
echo "========================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Error: Do not run this script as root. It will prompt for sudo when needed."
    exit 1
fi

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "Error: Python 3.10+ required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "Python version OK: $PYTHON_VERSION"

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# Set installation directory
INSTALL_DIR="/opt/anomalywatch"
CURRENT_DIR=$(pwd)

echo "Creating installation directory: $INSTALL_DIR"
sudo mkdir -p $INSTALL_DIR
sudo cp -r $CURRENT_DIR/* $INSTALL_DIR/
sudo chown -R $USER:$USER $INSTALL_DIR

# Create virtual environment
echo "Creating Python virtual environment..."
cd $INSTALL_DIR
python3 -m venv venv

# Activate virtual environment and install dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r deploy/requirements.txt

# Create required directories
echo "Creating required directories..."
mkdir -p models logs

# Create systemd user and group
echo "Creating system user..."
sudo useradd -r -s /bin/false anomalywatch 2>/dev/null || echo "User already exists"
sudo chown -R anomalywatch:anomalywatch $INSTALL_DIR

# Install systemd service
echo "Installing systemd service..."
sudo cp deploy/anomalywatch.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start service
echo "Enabling service..."
sudo systemctl enable anomalywatch.service

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "To start the service:"
echo "  sudo systemctl start anomalywatch"
echo ""
echo "To check status:"
echo "  sudo systemctl status anomalywatch"
echo ""
echo "To view logs:"
echo "  journalctl -u anomalywatch -f"
echo ""
echo "Dashboard URL (after starting):"
echo "  http://localhost:5000"
echo ""
echo "Note: First run will perform 15-minute baseline learning."
echo "========================================"
