#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot network connection issues
"""

import requests
import subprocess
import sys
import time
import os
from pathlib import Path

def check_backend_status():
    """Check if backend server is running"""
    print("🔍 Checking backend server status...")
    
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            print("✅ Backend server is running and responding")
            return True
        else:
            print(f"❌ Backend server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Backend server is not running or not accessible")
        return False
    except Exception as e:
        print(f"❌ Error connecting to backend: {e}")
        return False

def check_backend_endpoints():
    """Check if specific backend endpoints are working"""
    print("\n🔍 Testing backend endpoints...")
    
    endpoints = [
        ('/', 'Root endpoint'),
        ('/standard-headings', 'Standard headings endpoint'),
        ('/extracted-headings', 'Extracted headings endpoint'),
    ]
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f'http://localhost:8000{endpoint}', timeout=10)
            if response.status_code == 200:
                print(f"✅ {description}: OK")
            else:
                print(f"❌ {description}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {description}: Error - {e}")

def check_frontend_status():
    """Check if frontend server is running"""
    print("\n🔍 Checking frontend server status...")
    
    try:
        response = requests.get('http://localhost:3000/', timeout=5)
        if response.status_code == 200:
            print("✅ Frontend server is running and responding")
            return True
        else:
            print(f"❌ Frontend server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Frontend server is not running or not accessible")
        return False
    except Exception as e:
        print(f"❌ Error connecting to frontend: {e}")
        return False

def check_processes():
    """Check if backend and frontend processes are running"""
    print("\n🔍 Checking running processes...")
    
    try:
        # Check for Python processes running main.py
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True, shell=True)
        if 'main.py' in result.stdout:
            print("✅ Backend Python process is running")
        else:
            print("❌ Backend Python process not found")
            
        # Check for Node.js processes
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq node.exe'], 
                              capture_output=True, text=True, shell=True)
        if result.stdout.strip():
            print("✅ Node.js processes are running")
        else:
            print("❌ No Node.js processes found")
            
    except Exception as e:
        print(f"❌ Error checking processes: {e}")

def check_ports():
    """Check if ports 8000 and 3000 are in use"""
    print("\n🔍 Checking port usage...")
    
    try:
        # Check port 8000 (backend)
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
        if ':8000' in result.stdout and 'LISTENING' in result.stdout:
            print("✅ Port 8000 is in use (backend)")
        else:
            print("❌ Port 8000 is not in use")
            
        # Check port 3000 (frontend)
        if ':3000' in result.stdout and 'LISTENING' in result.stdout:
            print("✅ Port 3000 is in use (frontend)")
        else:
            print("❌ Port 3000 is not in use")
            
    except Exception as e:
        print(f"❌ Error checking ports: {e}")

def test_api_call():
    """Test a specific API call that might be failing"""
    print("\n🔍 Testing API call to process-all-files...")
    
    try:
        # Create a simple test file
        test_file_path = 'test_file.txt'
        with open(test_file_path, 'w') as f:
            f.write('Test content for API call')
        
        # Test the API call
        with open(test_file_path, 'rb') as f:
            files = {'files': ('test_file.txt', f, 'text/plain')}
            response = requests.post('http://localhost:8000/process-all-files', 
                                   files=files, timeout=30)
            
        if response.status_code == 200:
            print("✅ API call to /process-all-files successful")
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
        # Clean up test file
        os.remove(test_file_path)
        
    except Exception as e:
        print(f"❌ API call test failed: {e}")

def provide_solutions():
    """Provide solutions based on the diagnostic results"""
    print("\n" + "=" * 50)
    print("🔧 TROUBLESHOOTING SOLUTIONS")
    print("=" * 50)
    
    print("\n1. If backend is not running:")
    print("   cd Backend")
    print("   python main.py")
    
    print("\n2. If frontend is not running:")
    print("   cd Frontend")
    print("   npm start")
    
    print("\n3. If using the startup script:")
    print("   python start_app.py")
    
    print("\n4. Check if ports are blocked:")
    print("   - Try different ports in main.py and package.json")
    print("   - Check firewall settings")
    
    print("\n5. If CORS issues:")
    print("   - Backend should have CORS middleware configured")
    print("   - Check browser console for CORS errors")
    
    print("\n6. If API endpoints are not found:")
    print("   - Check if backend is running the correct version")
    print("   - Verify the endpoint URLs in the code")
    
    print("\n7. Browser troubleshooting:")
    print("   - Clear browser cache")
    print("   - Try incognito/private mode")
    print("   - Check browser console for errors")

def main():
    """Run all diagnostic checks"""
    print("🔍 SRS Dynamic Generator - Connection Diagnostic")
    print("=" * 50)
    
    # Run all checks
    backend_ok = check_backend_status()
    frontend_ok = check_frontend_status()
    
    if backend_ok:
        check_backend_endpoints()
        test_api_call()
    
    check_processes()
    check_ports()
    
    # Provide solutions
    provide_solutions()
    
    print("\n" + "=" * 50)
    if backend_ok and frontend_ok:
        print("✅ Both servers appear to be running correctly")
        print("   If you're still getting network errors, check the browser console")
    else:
        print("❌ One or more servers are not running properly")
        print("   Please start the servers using the solutions above")

if __name__ == "__main__":
    main() 