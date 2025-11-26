# azure_openai_client.py
from azure.identity import CertificateCredential, get_bearer_token_provider
from openai import AzureOpenAI
import httpx
import logging
from config import Config

logger = logging.getLogger(__name__)

def get_azure_openai_client() -> AzureOpenAI:
    # --- PROXY: Single URL (string) ---
    http_client = None
    proxy_url = Config.HTTPS_PROXY or Config.HTTP_PROXY
    if proxy_url:
        logger.info(f"Using proxy: {proxy_url}")
        try:
            transport = httpx.HTTPTransport(
                proxy=proxy_url,
                verify=True,
                # Increase connection timeout
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
            )
            http_client = httpx.Client(
                transport=transport,
                timeout=httpx.Timeout(60.0, connect=30.0),  # 60s read, 30s connect
                verify=True
            )
            logger.info("Proxy client created with 60s timeout")
        except Exception as e:
            logger.error(f"Failed to create proxy client: {e}")
            raise
    else:
        logger.info("No proxy configured")

    # --- SPN Auth ---
    try:
        credential = CertificateCredential(
            tenant_id=Config.AZURE_TENANT_ID,
            client_id=Config.AZURE_CLIENT_ID,
            certificate_path=Config.CERTIFICATE_PATH
        )
        token_provider = get_bearer_token_provider(
            credential, "https://management.azure.com/.default"
        )
        logger.info("SPN token provider ready")
    except Exception as e:
        logger.error(f"SPN auth failed: {e}")
        raise

    # --- Azure OpenAI Client with HIGH TIMEOUT ---
    client = AzureOpenAI(
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
        api_version="2024-08-01-preview",
        azure_ad_token_provider=token_provider,
        http_client=http_client,
        # Global timeout: 5 minutes (for large prompts)
        timeout=300.0
    )

    logger.info("Azure OpenAI client initialized with 300s timeout")
    return client
