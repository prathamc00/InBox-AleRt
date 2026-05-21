import inspect
import msal

app = msal.ConfidentialClientApplication(
    "client_id",
    client_credential="secret"
)

sig = inspect.signature(app.acquire_token_by_authorization_code)
print("acquire_token_by_authorization_code signature:")
print(sig)
