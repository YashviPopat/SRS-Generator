#!/usr/bin/env python3
"""
Environment Setup Script for SRS Dynamic Generator
This script helps you set up the required environment variables.
"""

import os
import sys
from dotenv import load_dotenv

def setup_environment():
    """Set up environment variables for the SRS Dynamic Generator"""

    print("🔧 Setting up environment variables for SRS Dynamic Generator")
    print("=" * 60)

    # Load .env file if it exists
    try:
        load_dotenv()
        print("✅ .env file loaded successfully")
    except Exception as e:
        print(f"⚠️ Warning: Could not load .env file: {e}")
    
    # Check if .env file exists
    env_file_path = ".env"
    if os.path.exists(env_file_path):
        print(f"✅ .env file already exists at: {os.path.abspath(env_file_path)}")
        print("📖 Current .env contents:")
        try:
            with open(env_file_path, 'r') as f:
                content = f.read()
                print(content)
        except Exception as e:
            print(f"❌ Error reading .env file: {e}")
    else:
        print(f"❌ .env file not found at: {os.path.abspath(env_file_path)}")
        print("💡 Creating .env file...")
        
        # Create .env file with template content
        env_content = """# API Keys for AI Services
GEMINI_API_KEY=AIzaSyDERZ7x4BcVGLwJM1ucGO02hFW2PTKodaQ

# Server Configuration
HOST=127.0.0.1
PORT=8000

# Development Settings
DEBUG=True
LOG_LEVEL=info

# File Upload Limits
MAX_FILE_SIZE=10485760  # 10MB in bytes
MAX_FILES_PER_REQUEST=10
"""
        
        try:
            with open(env_file_path, 'w') as f:
                f.write(env_content)
            print(f"✅ .env file created successfully at: {os.path.abspath(env_file_path)}")
        except Exception as e:
            print(f"❌ Error creating .env file: {e}")
            print("💡 Please create the .env file manually with the content above")
    
    print("\n🔍 Checking environment variables...")
    
    # Check required environment variables
    required_vars = ['GEMINI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:10]}... (set)")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("💡 Please set these variables in your .env file or system environment")
        print("\n📋 To set environment variables manually:")
        print("1. Create a .env file in the Backend directory")
        print("2. Add the required variables (see template above)")
        print("3. Restart your application")
        
        return False
    else:
        print(f"\n✅ All required environment variables are set!")
        return True

def test_gemini_connection():
    """Test the Gemini API connection"""
    print("\n🧪 Testing Gemini API connection...")
    
    try:
        import google.generativeai as genai
        
        # Get API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment variables")
            return False
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Test with a simple prompt
        response = model.generate_content("Hello, this is a test.")
        
        if response and response.text:
            print("✅ Gemini API connection successful!")
            print(f"📝 Test response: {response.text[:50]}...")
            return True
        else:
            print("❌ Gemini API returned empty response")
            return False
            
    except Exception as e:
        print(f"❌ Gemini API connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 SRS Dynamic Generator - Environment Setup")
    print("=" * 60)
    
    # Setup environment
    env_ok = setup_environment()
    
    if env_ok:
        # Test Gemini connection
        gemini_ok = test_gemini_connection()
        
        if gemini_ok:
            print("\n🎉 Environment setup completed successfully!")
            print("🚀 You can now run your SRS Dynamic Generator application")
        else:
            print("\n⚠️ Environment setup completed, but Gemini API test failed")
            print("💡 Please check your API key and try again")
    else:
        print("\n❌ Environment setup incomplete")
        print("💡 Please fix the issues above and run this script again")
    
    print("\n" + "=" * 60) 