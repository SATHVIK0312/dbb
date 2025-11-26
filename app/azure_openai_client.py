"""
Azure OpenAI Client Utility
Centralized module for all Azure OpenAI API calls with system role only.
"""

import os
import logging
from typing import Optional, Dict, Any
from azure.identity import CertificateCredential
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


def get_access_token() -> str:
    """
    Fetch Azure access token using certificate credentials.
    Uses local certificate file for authentication.
    """
    try:
        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        cert_path = os.path.join(dir_path, "JPMC1||certs", "uatagent.azure.jpmchase.new.pem")
        
        scope = "https://cognitiveservices.azure.com/.default"
        credential = CertificateCredential(
            client_id=os.environ.get("AZURE_CLIENT_ID"),
            certificate_path=cert_path,
            tenant_id=os.environ.get("AZURE_TENANT_ID"),
            logging_enable=False
        )
        
        access_token = credential.get_token(scope).token
        logger.info("Azure access token retrieved successfully")
        return access_token
    except Exception as e:
        logger.error(f"Failed to get access token: {str(e)}")
        raise


def get_azure_openai_client() -> AzureOpenAI:
    """
    Initialize and return Azure OpenAI client with certificate-based authentication.
    """
    try:
        access_token = get_access_token()
        
        client = AzureOpenAI(
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            default_headers={
                "Authorization": f"Bearer {access_token}",
                "user_sid": "REPLACE"
            }
        )
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
        raise


def call_openai_api(
    prompt: str,
    max_tokens: int = 2000,
    temperature: float = 0.7,
    system_message: Optional[str] = None
) -> str:
    """
    Call Azure OpenAI API with system role only.
    
    Args:
        prompt: The user prompt/question
        max_tokens: Maximum tokens in response
        temperature: Temperature for response generation
        system_message: System role message (optional)
    
    Returns:
        Text response from the model
    """
    try:
        client = get_azure_openai_client()
        
        messages = [
            {
                "role": "system",
                "content": system_message or "You are a helpful assistant. Respond with only valid output, no explanations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_MODEL", "gpt-4"),
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Azure OpenAI API call failed: {str(e)}")
        raise


def call_openai_with_images(
    prompt: str,
    image_b64: Optional[str] = None,
    max_tokens: int = 2000,
    system_message: Optional[str] = None
) -> str:
    """
    Call Azure OpenAI API with image support (Vision).
    
    Args:
        prompt: The user prompt
        image_b64: Base64 encoded image data
        max_tokens: Maximum tokens in response
        system_message: System role message
    
    Returns:
        Text response from the model
    """
    try:
        client = get_azure_openai_client()
        
        messages = [
            {
                "role": "system",
                "content": system_message or "You are a helpful assistant. Respond with only valid output, no explanations."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        # Add image if provided
        if image_b64:
            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_b64}"
                }
            })
        
        response = client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_MODEL", "gpt-4-vision"),
            messages=messages,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Azure OpenAI API call with images failed: {str(e)}")
        raise
