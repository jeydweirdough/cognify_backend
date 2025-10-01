"""
Diagnostic script to check if your environment is properly configured for OAuth
Run this before starting your FastAPI server
"""

import sys
import os

print("="*60)
print("COGNIFY OAUTH DIAGNOSTICS")
print("="*60)
print()

# Check 1: Python version
print("1. Checking Python version...")
python_version = sys.version_info
print(f"   Python {python_version.major}.{python_version.minor}.{python_version.micro}")
if python_version.major == 3 and python_version.minor >= 8:
    print("   ✅ Python version is compatible")
else:
    print("   ⚠️  Python 3.8+ recommended")
print()

# Check 2: Required packages
print("2. Checking required packages...")
required_packages = {
    'fastapi': 'FastAPI framework',
    'uvicorn': 'ASGI server',
    'firebase_admin': 'Firebase Admin SDK',
    'pyrebase': 'Firebase client',
    'authlib': 'OAuth library',
    'itsdangerous': 'Session signing (CRITICAL for OAuth)',
    'dotenv': 'Environment variables (python-dotenv)',
    'starlette': 'ASGI framework'
}

missing_packages = []
for package, description in required_packages.items():
    try:
        __import__(package.replace('-', '_'))
        print(f"   ✅ {package:20s} - {description}")
    except ImportError:
        print(f"   ❌ {package:20s} - {description} (MISSING)")
        missing_packages.append(package)

print()

if missing_packages:
    print("❌ MISSING PACKAGES FOUND!")
    print(f"   Run: pip install {' '.join(missing_packages)}")
    print()
else:
    print("✅ All required packages are installed!")
    print()

# Check 3: .env file
print("3. Checking .env file...")
if os.path.exists('.env'):
    print("   ✅ .env file exists")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'SESSION_SECRET_KEY',
        'FIREBASE_API_KEY',
        'FIREBASE_PROJECT_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value and value != '':
            if var == 'SESSION_SECRET_KEY':
                # Check if it's the default weak key
                weak_keys = ['secretkey', 'change-this', 'your-secret-key']
                if any(weak in value.lower() for weak in weak_keys):
                    print(f"   ⚠️  {var:25s} - Set but using weak/default key!")
                    print(f"      Generate a strong key: python -c \"import secrets; print(secrets.token_hex(32))\"")
                else:
                    print(f"   ✅ {var:25s} - Set")
            else:
                print(f"   ✅ {var:25s} - Set")
        else:
            print(f"   ❌ {var:25s} - NOT SET")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n   ❌ Missing environment variables: {', '.join(missing_vars)}")
    print()
else:
    print("   ❌ .env file not found!")
    print("      Create a .env file with your configuration")
    print()

# Check 4: Service account key
print("4. Checking Firebase service account key...")
service_account = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'serviceAccountKey.json')
if os.path.exists(service_account):
    print(f"   ✅ {service_account} exists")
else:
    print(f"   ❌ {service_account} not found!")
    print("      Download from Firebase Console → Project Settings → Service Accounts")
print()

# Check 5: itsdangerous specifically (most common issue)
print("5. Checking itsdangerous (CRITICAL for OAuth sessions)...")
try:
    import itsdangerous
    print(f"   ✅ itsdangerous version {itsdangerous.__version__} installed")
    
    # Test if it can sign data
    from itsdangerous import URLSafeTimedSerializer
    serializer = URLSafeTimedSerializer("test-key")
    test_data = serializer.dumps({"test": "data"})
    decoded = serializer.loads(test_data)
    print("   ✅ Session signing test passed")
except ImportError:
    print("   ❌ itsdangerous NOT INSTALLED - OAuth will FAIL!")
    print("      This is the most common cause of 'mismatching_state' error")
    print("      Run: pip install itsdangerous")
except Exception as e:
    print(f"   ⚠️  Session signing test failed: {e}")
print()

# Check 6: Port availability
print("6. Checking if port 8000 is available...")
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 8000))
sock.close()

if result == 0:
    print("   ⚠️  Port 8000 is already in use!")
    print("      Stop any running servers or use a different port")
else:
    print("   ✅ Port 8000 is available")
print()

# Summary
print("="*60)
print("SUMMARY")
print("="*60)

if missing_packages:
    print("❌ SETUP INCOMPLETE - Missing packages")
    print(f"\nQuick fix:")
    print(f"pip install {' '.join(missing_packages)}")
elif 'itsdangerous' in [p for p in required_packages.keys()]:
    try:
        import itsdangerous
        print("✅ SETUP LOOKS GOOD!")
        print("\nYou can now start your server:")
        print("python main.py")
        print("\nThen test Google OAuth:")
        print("http://localhost:8000/login/google")
    except ImportError:
        print("❌ CRITICAL: itsdangerous is not installed")
        print("\nRun this command:")
        print("pip install itsdangerous")
else:
    print("⚠️  Some issues found - review above")

print("="*60)