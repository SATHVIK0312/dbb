# config.py
import os
from pathlib import Path

class Config:
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource.openai.azure.com/")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    
    # SPN Certificate Auth
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    CERTIFICATE_PATH = os.getenv("CERTIFICATE_PATH", "certs/spn-cert.pem")  # .pem file path
    
    # Proxy (if behind corporate proxy)
    HTTP_PROXY = os.getenv("HTTP_PROXY", "http://proxy.corp.com:8080")
    HTTPS_PROXY = os.getenv("HTTPS_PROXY", "http://proxy.corp.com:8080")

    @staticmethod
    def validate():
        required = ["AZURE_TENANT_ID", "AZURE_CLIENT_ID"]
        missing = [k for k in required if not getattr(Config, k)]
        if missing:
            raise ValueError(f"Missing required env vars: {missing}")
        if not Path(Config.CERTIFICATE_PATH).exists():
            raise FileNotFoundError(f"Certificate not found: {Config.CERTIFICATE_PATH}")

# Load and validate on import
Config.validate()
