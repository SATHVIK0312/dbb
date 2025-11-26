# azure_openai_client.py
from azure.identity import CertificateCredential
from openai import AzureOpenAI
import os
import httpx
from config import Config

def get_azure_openai_client() -> AzureOpenAI:
    """
    Initialize Azure OpenAI client using SPN + .pem certificate + proxy
    """
    # Setup proxy (if configured)
    proxies = None
    if Config.HTTP_PROXY or Config.HTTPS_PROXY:
        proxies = {
            "http://": Config.HTTP_PROXY,
            "https://": Config.HTTPS_PROXY,
        }

    # Use httpx client with proxy
    transport = httpx.HTTPTransport(proxy=proxies) if proxies else None

    # Authenticate using certificate
    credential = CertificateCredential(
        tenant_id=Config.AZURE_TENANT_ID,
        client_id=Config.AZURE_CLIENT_ID,
        certificate_path=Config.CERTIFICATE_PATH
    )

    # Get access token
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    
    # Initialize Azure OpenAI client
    client = AzureOpenAI(
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
        api_version="2024-05-01-preview",
        azure_ad_token=token.token,  # Direct token injection
        http_client=httpx.Client(transport=transport, verify=True) if transport else None
    )

    return client
