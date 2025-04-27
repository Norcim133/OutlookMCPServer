import os
from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions, AuthenticationRecord
from msgraph import GraphServiceClient
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class AzureSettings:
    """
    Manages authentication with Azure GraphController API
    Assumes .env storing client_id, tenant_id, and scopes in environment variables
    Stores authentication record in auth_cache directory (creates directory if needed)
    Claude Desktop can't trigger interactive authentication challenges (e.g. in browser)
    Azure's DeviceCodeCredential allows authentication challenge (url, code) via text that Claude can serve to user
    """
    def __init__(self):
        # Load configuration from environment variables
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.scopes = self._get_scopes()

        # Create .env file with these values if it doesn't exist
        if not self.client_id or not self.tenant_id or not self.scopes:
            raise ValueError("Missing one of AZURE_CLIENT_ID, AZURE_TENANT_ID, or AZURE_GRAPH_SCOPES in .env")

        self.cache_options = TokenCachePersistenceOptions(
            name="OutlookMCP",
            allow_unencrypted_storage=False  # Use secure storage
        )

        # Set up paths
        self.auth_cache_dir = Path(__file__).parent / "auth_cache"
        self.auth_record_path = self.auth_cache_dir / "auth_record.json"

        # Authentication state
        self.credential = None
        self.user_client = None
        logging.info("AzureSettings initialized")
        # Configure cache options

    def _get_scopes(self):
        """Ensures scopes from environment variable are valid and split into a list of strings"""
        raw_scopes = os.getenv("AZURE_GRAPH_SCOPES", "")
        if not raw_scopes:
            return None
        scopes = raw_scopes.strip().split()
        return scopes

    def get_client_from_silent_auth(self):
        """Fetch existing credential, return None if not found
        """
        # If no auth_record returns none so auth wrapper can trigger interactive auth
        logging.info("Checking for existing authentication record")
        if not os.path.exists(self.auth_record_path):
            logging.info("No authentication record found")
            return None

        try:
            # If auth record exists, attempts to load it
            with open(self.auth_record_path, "r") as file:
                auth_record_json = file.read()
                auth_record = AuthenticationRecord.deserialize(auth_record_json)


            # Create credential with the authentication record (silent auth)
            self.credential = DeviceCodeCredential(
                client_id=self.client_id,
                tenant_id=self.tenant_id,
                cache_persistence_options=self.cache_options,
                authentication_record=auth_record
            )


            self.user_client = GraphServiceClient(
                credentials=self.credential,
                scopes=self.scopes
            )
            logging.info("Loaded existing authentication record")
            return self.user_client
        except Exception as e:
            logging.error(f"Error loading existing authentication record: {str(e)}")
            return None

    def get_auth_instructions(self):
        """Return authentication instructions from Azure, to bot, for the user to auth in browser"""
        logging.info("Starting interactive authentication")
        auth_info = {"url": None, "code": None}

        # Takes the auth_info dict from the outer scope so, when called by authenticate, we can access the dict values
        def prompt_callback(url, code, expiration=None, *args, **kwargs):
            auth_info["url"] = url
            auth_info["code"] = code
            logging.info(f"Got device code: URL={url}, code={code}, expires={expiration}")
            return None

        # Create the credential
        self.credential = DeviceCodeCredential(
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            cache_persistence_options=self.cache_options,
            prompt_callback=prompt_callback
        )

        # Just trigger the callback - don't wait for auth to complete
        import threading

        # The callback will execute immediately in the thread, giving us access to auth flow strings
        # Main thread: returns auth instructions to bot
        # Auth thread: waits for user to complete auth in browser, saves auth record, creates client
        # If success, user can retry their request without having to reauthenticate
        def auth_thread():
            try:
                # This will call prompt_callback immediately and then block waiting for auth
                auth_record = self.credential.authenticate(scopes=self.scopes)

                # If we get here, user completed auth - save the record
                with open(self.auth_record_path, "w") as file:
                    file.write(auth_record.serialize())
                logging.info(f"Authentication succeeded, record saved to {self.auth_record_path}")

                # Create the client
                self.user_client = GraphServiceClient(
                    credentials=self.credential,
                    scopes=self.scopes
                )
            except Exception as e:
                logging.info(f"Auth thread: {str(e)}")

        # Start in background thread
        t = threading.Thread(target=auth_thread)
        t.daemon = True
        t.start()

        # Wait briefly for callback
        import time
        time.sleep(2)

        # Return auth instructions
        if auth_info["url"] and auth_info["code"]:
            return f"""
    Please authenticate this application in browser.

    1. Visit this URL: {auth_info['url']}
    2. Enter the code: {auth_info['code']}

    After authenticating, please retry your request.
    """
        else:
            return "Failed to get authentication code. Please try again."

    def get_user_client(self) -> Optional[GraphServiceClient]:
        """Get an authenticated GraphServiceClient if available"""
        logging.info("Getting authenticated GraphServiceClient")
        if self.user_client is not None:
            logging.info("GraphServiceClient already set")
            return self.user_client

        if self.get_client_from_silent_auth():
            logging.info("Loading existing authenticated GraphServiceClient")
            return self.user_client

        # Returns None if no authenticated client is available
        # Auth wrapper will use this to trigger interactive auth if needed
        logging.info("No graph_client; returning None")
        return None