# azure_openai_client.py
from azure.identity import CertificateCredential, get_bearer_token_provider
from openai import AzureOpenAI
import httpx
import logging
from config import Config

logger = logging.getLogger(__name__)

def get_azure_openai_client() -> AzureOpenAI:
    # --- PROXY: CORRECT FORMAT FOR HTTPX ---
    http_client = None
    if Config.HTTP_PROXY or Config.HTTPS_PROXY:
        # Use a single proxy URL (most common)
        proxy_url = Config.HTTPS_PROXY or Config.HTTP_PROXY  # Prefer HTTPS
        if proxy_url:
            logger.info(f"Using proxy: {proxy_url}")
            transport = httpx.HTTPTransport(proxy=proxy_url)  # ← STRING, NOT DICT
            http_client = httpx.Client(transport=transport, verify=True)
        else:
            logger.warning("Proxy env vars set but empty")
    else:
        logger.info("No proxy configured")

    # --- SPN + Certificate Auth ---
    credential = CertificateCredential(
        tenant_id=Config.AZURE_TENANT_ID,
        client_id=Config.AZURE_CLIENT_ID,
        certificate_path=Config.CERTIFICATE_PATH
    )

    token_provider = get_bearer_token_provider(
        credential, "https://management.azure.com/.default"
    )

    # --- Create Azure OpenAI Client ---
    client = AzureOpenAI(
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
        api_version="2024-08-01-preview",
        azure_ad_token_provider=token_provider,
        http_client=http_client  # ← Works with proxy or None
    )

    logger.info("Azure OpenAI client initialized successfully")
    return client
