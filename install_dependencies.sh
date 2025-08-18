#!/bin/bash

echo "========================================"
echo "SRS Dynamic Generator - Dependencies Setup"
echo "========================================"
echo

echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi
echo "✅ Python is installed"

echo
echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed or not in PATH"
    echo "Please install Node.js from https://nodejs.org"
    exit 1
fi
echo "✅ Node.js is installed"

echo
echo "Checking npm installation..."
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed or not in PATH"
    echo "Please install npm (usually comes with Node.js)"
    exit 1
fi
echo "✅ npm is installed"

echo
echo "========================================"
echo "Installing Python Dependencies"
echo "========================================"
echo

cd "$(dirname "$0")/Backend"

echo "Installing Python packages from requirements.txt..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi
echo "✅ Python dependencies installed successfully"

echo
echo "========================================"
echo "Installing Mermaid CLI (Required for Diagrams)"
echo "========================================"
echo

echo "Installing Mermaid CLI globally..."
npm install -g @mermaid-js/mermaid-cli
if [ $? -ne 0 ]; then
    echo "❌ Failed to install Mermaid CLI globally"
    echo "Trying alternative installation method..."
    npm install -g mermaid-cli
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Mermaid CLI"
        echo "This will prevent diagram generation from working"
        echo "You can try installing it manually later with:"
        echo "npm install -g @mermaid-js/mermaid-cli"
    else
        echo "✅ Mermaid CLI installed successfully (alternative method)"
    fi
else
    echo "✅ Mermaid CLI installed successfully"
fi

echo
echo "Verifying Mermaid CLI installation..."
if ! command -v mmdc &> /dev/null; then
    echo "⚠️  Mermaid CLI verification failed"
    echo "This may cause diagram generation to fail"
    echo "Try restarting your terminal and running: mmdc --version"
else
    echo "✅ Mermaid CLI is working correctly"
fi

echo
echo "========================================"
echo "Installing Frontend Dependencies"
echo "========================================"
echo

cd "$(dirname "$0")/Frontend"

echo "Installing Node.js packages..."
npm install
if [ $? -ne 0 ]; then
    echo "❌ Failed to install frontend dependencies"
    exit 1
fi
echo "✅ Frontend dependencies installed successfully"

echo
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo
echo "✅ All dependencies have been installed"
echo
echo "To start the application:"
echo "1. Run: python3 start_app.py"
echo "2. Or start backend and frontend separately:"
echo "   - Backend: cd Backend && python3 main.py"
echo "   - Frontend: cd Frontend && npm start"
echo
echo "If diagram generation still fails:"
echo "1. Restart your terminal"
echo "2. Verify Mermaid CLI: mmdc --version"
echo "3. If needed, manually install: npm install -g @mermaid-js/mermaid-cli"
echo 