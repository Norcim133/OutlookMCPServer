from dataclasses import dataclass
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env into environment

@dataclass
class AzureSettings:
    client_id: str
    tenant_id: str
    scopes: List[str]

    def __init__(self):
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        raw_scopes = os.getenv("AZURE_GRAPH_SCOPES", "")

        if not self.client_id or not self.tenant_id or not raw_scopes:
            raise ValueError("Missing one of AZURE_CLIENT_ID, AZURE_TENANT_ID, or AZURE_GRAPH_SCOPES in .env")

        self.scopes = raw_scopes.strip().split()
