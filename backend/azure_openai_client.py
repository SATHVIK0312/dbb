# azure_openai_client.py
from azure.identity import CertificateCredential, get_bearer_token_provider
from openai import AzureOpenAI
import httpx
import logging
from config import Config

logger = logging.getLogger(__name__)

def get_azure_openai_client() -> AzureOpenAI:
    # --- PROXY: CORRECT FORMAT (string values) ---
    proxies = None
    if Config.HTTP_PROXY or Config.HTTPS_PROXY:
        proxies = {
            "http://": Config.HTTP_PROXY,      # ← string
            "https://": Config.HTTPS_PROXY     # ← string
        }
        # httpx expects dict with protocol:// keys → string values
        transport = httpx.HTTPTransport(proxy=proxies)
        http_client = httpx.Client(transport=transport, verify=True)
    else:
        http_client = None

    # --- SPN + Cert Auth (correct audience) ---
    credential = CertificateCredential(
        tenant_id=Config.AZURE_TENANT_ID,
        client_id=Config.AZURE_CLIENT_ID,
        certificate_path=Config.CERTIFICATE_PATH
    )

    token_provider = get_bearer_token_provider(
        credential, "https://management.azure.com/.default"
    )

    client = AzureOpenAI(
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
        api_version="2024-08-01-preview",
        azure_ad_token_provider=token_provider,
        http_client=http_client
    )

    logger.info("Azure OpenAI client initialized with SPN + proxy")
    return client
