# config.py
import os
from pathlib import Path
from typing import List

# ----------------------------------------------------------------------
# 1. Load .env **first** – this runs before any class is defined
# ----------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()                     # <-- reads .env in the cwd
except Exception:                     # dotenv is optional in prod
    pass


class Config:
    # ------------------------------------------------------------------
    # 2. Pull values from the environment (ALL CAPS, underscores)
    # ------------------------------------------------------------------
    AZURE_OPENAI_ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    AZURE_TENANT_ID         = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_ID         = os.getenv("AZURE_CLIENT_ID")
    CERTIFICATE_PATH        = os.getenv("CERTIFICATE_PATH", "certs/spn-cert.pem")

    HTTP_PROXY              = os.getenv("HTTP_PROXY")
    HTTPS_PROXY             = os.getenv("HTTPS_PROXY")

    # ------------------------------------------------------------------
    # 3. Validation – runs **once** when the module is imported
    # ------------------------------------------------------------------
    @staticmethod
    def _missing_vars() -> List[str]:
        required = ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_OPENAI_ENDPOINT"]
        return [name for name in required if not getattr(Config, name)]

    @staticmethod
    def validate():
        missing = Config._missing_vars()
        if missing:
            raise RuntimeError(
                "Config validation failed – missing required env vars: "
                f"{', '.join(missing)}"
            )

        cert_path = Path(Config.CERTIFICATE_PATH)
        if not cert_path.is_file():
            raise FileNotFoundError(
                f"Certificate not found or not a file: {cert_path.resolve()}"
            )

# ----------------------------------------------------------------------
# 4. Run validation **immediately** – fails fast if something is wrong
# ----------------------------------------------------------------------
Config.validate()
