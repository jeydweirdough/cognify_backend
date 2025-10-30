import requests
import json

# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8000"

# --- !! IMPORTANT !! ---
# Manually create this user in your Firebase Authentication console
# or use an existing user.
LOGIN_EMAIL = "your-test-email@gmail.com"
LOGIN_PASSWORD = "your-test-password"
# ---------------------

def get_auth_token():
    """Logs in to the API to get a fresh ID token."""
    print(f"Attempting login to {BASE_URL}/auth/login as {LOGIN_EMAIL}...")
    
    login_payload = {
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
        
        if response.status_code != 200:
            print(f"Login Failed! Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        data = response.json()
        token = data.get("token")
        
        if not token:
            print("Login successful, but no 'token' found in response.")
            return None
            
        print("✅ Login successful, token acquired.")
        return token
        
    except requests.ConnectionError:
        print(f"❌ Connection Error: Could not connect to {BASE_URL}.")
        print("Is your FastAPI server running? (Run: uvicorn main:app --reload)")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def test_authenticated_endpoint(token: str):
    """Tests an authenticated endpoint (e.g., /profiles/)."""
    print("\nAttempting to fetch /profiles/ with token...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/profiles/", headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Successfully fetched personal profile:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("❌ Failed to fetch profile:")
            print(response.text)
            
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    auth_token = get_auth_token()
    
    if auth_token:
        test_authenticated_endpoint(auth_token)
    else:
        print("\nSkipping authenticated endpoint test since login failed.")