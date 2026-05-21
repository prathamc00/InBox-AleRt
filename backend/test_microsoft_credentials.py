import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

import msal
from core.config import settings

def main():
    print("Testing Microsoft Client ID and Secret validity...")
    print(f"Client ID: {settings.MICROSOFT_CLIENT_ID}")
    
    try:
        app = msal.ConfidentialClientApplication(
            settings.MICROSOFT_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}",
            client_credential=settings.MICROSOFT_CLIENT_SECRET,
        )
        
        print("Acquiring token using client credentials...")
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "error" in result:
            print("[ERROR] Microsoft API returned an error:")
            print(f"Error Code: {result.get('error')}")
            print(f"Description: {result.get('error_description')}")
        else:
            print("[SUCCESS] Microsoft credentials are 100% VALID!")
            print("Successfully acquired application token!")
    except Exception as e:
        print(f"[EXCEPTION] Exception occurred: {e}")

if __name__ == "__main__":
    main()
