# authenticate.py
import os
from pathlib import Path
from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions
from settings import AzureSettings


def main():
    print("Starting standalone authentication for OutlookMCP")

    # Load settings
    settings = AzureSettings()
    client_id = settings.client_id
    tenant_id = settings.tenant_id
    graph_scopes = settings.scopes

    print(f"Using client_id: {client_id}")
    print(f"Using tenant_id: {tenant_id}")
    print(f"Using scopes: {graph_scopes}")

    # Set up cache options
    cache_options = TokenCachePersistenceOptions(
        name="OutlookMCP",
        allow_unencrypted_storage=False
    )

    # Create auth_cache directory if it doesn't exist
    auth_cache_dir = Path(__file__).parent / "auth_cache"
    if not os.path.exists(auth_cache_dir):
        os.makedirs(auth_cache_dir, exist_ok=True)
        print(f"Created auth_cache directory at: {auth_cache_dir}")

    auth_record_path = auth_cache_dir / "auth_record.json"
    print(f"Auth record will be saved to: {auth_record_path}")

    def prompt_callback(url, code, expiration=None, *args, **kwargs):
        """Display authentication instructions with URL and code"""
        print("\n\nAUTHENTICATION REQUIRED:")
        print(f"1. Go to: {url}")
        print(f"2. Enter code: {code}")
        if expiration:
            print(f"3. Complete before: {expiration}")
        print("\nAfter authenticating, you'll be able to use the Microsoft Graph API.\n")
        return None

    # Create credential with device code flow
    credential = DeviceCodeCredential(
        client_id=client_id,
        tenant_id=tenant_id,
        cache_persistence_options=cache_options,
        prompt_callback=prompt_callback
    )

    try:
        print("Starting authentication flow...")
        # Authenticate
        auth_record = credential.authenticate(scopes=graph_scopes)

        # Save auth record to file
        with open(auth_record_path, "w") as file:
            file.write(auth_record.serialize())

        print(f"Authentication successful! Auth record saved to {auth_record_path}")
        print("You can now run the MCP server.")
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        print("Please check your Azure application settings and try again.")


if __name__ == "__main__":
    main()