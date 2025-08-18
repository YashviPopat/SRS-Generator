#!/usr/bin/env python3
"""
Startup script for SRS Dynamic Generator
This script helps start both the backend and frontend servers
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_node_version():
    """Check if Node.js is installed"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js version: {result.stdout.strip()}")
            return True
        else:
            print("❌ Node.js not found")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found. Please install Node.js from https://nodejs.org/")
        return False

def check_npm():
    """Check if npm is installed"""
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm version: {result.stdout.strip()}")
            return True
        else:
            print("❌ npm not found")
            return False
    except FileNotFoundError:
        print("❌ npm not found. Please install npm")
        return False

def install_backend_dependencies():
    """Install backend Python dependencies"""
    print("\n📦 Installing backend dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'Backend/requirements.txt'], 
                      check=True, cwd='.')
        print("✅ Backend dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install backend dependencies: {e}")
        return False

def install_frontend_dependencies():
    """Install frontend Node.js dependencies"""
    print("\n📦 Installing frontend dependencies...")
    try:
        subprocess.run(['npm', 'install'], check=True, cwd='Frontend')
        print("✅ Frontend dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install frontend dependencies: {e}")
        return False

def check_environment():
    """Check if environment variables are set"""
    gemini_key = os.getenv('GEMINI_API_KEY')
    if gemini_key:
        print("✅ Gemini API key is configured")
        return True
    else:
        print("⚠️  Gemini API key not found")
        print("   Please set GEMINI_API_KEY environment variable")
        print("   You can create a .env file in the Backend directory with:")
        print("   GEMINI_API_KEY=your_api_key_here")
        return False

def start_backend():
    """Start the backend server"""
    print("\n🚀 Starting backend server...")
    try:
        # Start backend in a subprocess
        backend_process = subprocess.Popen(
            [sys.executable, 'main.py'],
            cwd='Backend',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        time.sleep(3)
        
        # Check if server is running
        try:
            response = requests.get('http://localhost:8000/', timeout=5)
            if response.status_code == 200:
                print("✅ Backend server is running on http://localhost:8000")
                return backend_process
            else:
                print(f"❌ Backend server responded with status {response.status_code}")
                return None
        except requests.exceptions.ConnectionError:
            print("❌ Backend server failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return None

def start_frontend():
    """Start the frontend server"""
    print("\n🚀 Starting frontend server...")
    try:
        # Start frontend in a subprocess
        frontend_process = subprocess.Popen(
            ['npm', 'start'],
            cwd='Frontend',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        time.sleep(5)
        
        print("✅ Frontend server is starting on http://localhost:3000")
        print("   It may take a moment to fully load...")
        return frontend_process
        
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        return None

def main():
    """Main startup function"""
    print("🎯 SRS Dynamic Generator - Startup Script")
    print("=" * 50)
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    if not check_node_version():
        sys.exit(1)
    
    if not check_npm():
        sys.exit(1)
    
    # Check if dependencies need to be installed
    backend_requirements = Path('Backend/requirements.txt')
    frontend_package_json = Path('Frontend/package.json')
    frontend_node_modules = Path('Frontend/node_modules')
    
    if backend_requirements.exists():
        print("\n🔍 Checking backend dependencies...")
        if not install_backend_dependencies():
            sys.exit(1)
    
    if frontend_package_json.exists() and not frontend_node_modules.exists():
        print("\n🔍 Checking frontend dependencies...")
        if not install_frontend_dependencies():
            sys.exit(1)
    
    # Check environment
    check_environment()
    
    print("\n" + "=" * 50)
    print("🚀 Starting SRS Dynamic Generator...")
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print("❌ Failed to start backend. Exiting.")
        sys.exit(1)
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print("❌ Failed to start frontend. Exiting.")
        backend_process.terminate()
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 SRS Dynamic Generator is starting up!")
    print("\n📱 Access the application:")
    print("   Frontend: http://localhost:3000")
    print("   Backend API: http://localhost:8000")
    print("\n📋 Next steps:")
    print("   1. Wait for the frontend to fully load")
    print("   2. Click 'Upload & Generate SRS'")
    print("   3. Upload your meeting summary PDFs")
    print("   4. Generate your SRS document!")
    print("\n⚠️  To stop the servers, press Ctrl+C")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping servers...")
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        print("✅ Servers stopped")

if __name__ == "__main__":
    main() 