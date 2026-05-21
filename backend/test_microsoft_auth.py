import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

import msal
from core.config import settings
from auth.microsoft import SCOPES

def main():
    print("Testing MSAL app building and auth URL generation...")
    try:
        app = msal.ConfidentialClientApplication(
            settings.MICROSOFT_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}",
            client_credential=settings.MICROSOFT_CLIENT_SECRET,
        )
        print("MSAL ConfidentialClientApplication successfully built!")
        
        auth_url = app.get_authorization_request_url(
            scopes=SCOPES,
            state="test_state_123456",
            redirect_uri=settings.MICROSOFT_REDIRECT_URI,
        )
        print("Auth URL successfully generated!")
        print(f"URL: {auth_url}")
    except Exception as e:
        print(f"Error during MSAL setup/URL generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
