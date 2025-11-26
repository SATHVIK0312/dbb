# config.py
import os
from pathlib import Path

class Config:
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    
    # SPN Certificate Auth
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    CERTIFICATE_PATH = os.getenv("CERTIFICATE_PATH", "certs/spn-cert.pem")

    # Proxy
    HTTP_PROXY = os.getenv("HTTP_PROXY")
    HTTPS_PROXY = os.getenv("HTTPS_PROXY")

    @staticmethod
    def validate():
        required_env_vars = [
            "AZURE_TENANT_ID",
            "AZURE_CLIENT_ID",
            "AZURE_OPENAI_ENDPOINT",
        ]
        missing = []
        for var_name in required_env_vars:
            if not getattr(Config, var_name):
                missing.append(var_name)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Validate cert file
        cert_path = Path(Config.CERTIFICATE_PATH)
        if not cert_path.exists():
            raise FileNotFoundError(f"Certificate not found: {cert_path.resolve()}")
        if not cert_path.is_file():
            raise ValueError(f"Certificate path is not a file: {cert_path}")

# Validate on import
try:
    Config.validate()
except Exception as e:
    raise RuntimeError(f"Config validation failed: {e}") from e
