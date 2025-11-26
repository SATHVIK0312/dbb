# config.py
import os
from pathlib import Path
from typing import List

# --------------------------------------------------------------
# 1. OPTIONAL: load .env (remove if you set vars elsewhere)
# --------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()                     # reads .env in cwd
    print("[DEBUG] .env loaded")
except Exception as e:
    print(f"[DEBUG] dotenv not available: {e}")

# --------------------------------------------------------------
# 2. Print EVERYTHING we see (run this **once**)
# --------------------------------------------------------------
print("\n=== ENV DEBUG DUMP ===")
_debug_vars = [
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_OPENAI_ENDPOINT",
    "CERTIFICATE_PATH",
    "HTTP_PROXY",
    "HTTPS_PROXY",
]
for v in _debug_vars:
    val = os.getenv(v)
    print(f"{v} = {val!r}")
print("=== END DUMP ===\n")

# --------------------------------------------------------------
# 3. Config class
# --------------------------------------------------------------
class Config:
    AZURE_OPENAI_ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    AZURE_TENANT_ID         = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_ID         = os.getenv("AZURE_CLIENT_ID")
    CERTIFICATE_PATH        = os.getenv("CERTIFICATE_PATH", "certs/spn-cert.pem")

    HTTP_PROXY              = os.getenv("HTTP_PROXY")
    HTTPS_PROXY             = os.getenv("HTTPS_PROXY")

    @staticmethod
    def _missing() -> List[str]:
        req = ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_OPENAI_ENDPOINT"]
        return [n for n in req if not getattr(Config, n)]

    @staticmethod
    def validate():
        missing = Config._missing()
        if missing:
            raise RuntimeError(
                "Config validation failed – missing env vars: "
                f"{', '.join(missing)}"
            )
        cert = Path(Config.CERTIFICATE_PATH)
        if not cert.is_file():
            raise FileNotFoundError(f"Cert not found: {cert.resolve()}")

# --------------------------------------------------------------
# 4. Run validation **immediately**
# --------------------------------------------------------------
Config.validate()
print("[SUCCESS] Config validated")
