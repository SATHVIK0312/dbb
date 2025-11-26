import os
import json
import logging
from fastapi import Body, Depends, HTTPException
from openai import AzureOpenAI
from azure.identity import CertificateCredential

# === CONFIG (from .env) ===
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

# === HARD-CODED CERT PATH (as in your function) ===
CERT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    "JPMC1||certs", "uatagent.azure.jpmchase.new.pem"
)

# === INLINE: get_access_token() ===
def get_access_token():
    if not os.path.exists(CERT_PATH):
        raise RuntimeError(f"Cert not found: {CERT_PATH}")
    
    scope = "https://cognitiveservices.azure.com/.default"
    try:
        credential = CertificateCredential(
            tenant_id=AZURE_TENANT_ID,
            client_id=AZURE_CLIENT_ID,
            certificate_path=CERT_PATH
        )
        token = credential.get_token(scope).token
        logging.info(f"SPN Token acquired: {token[:20]}...")
        return token
    except Exception as e:
        logging.error(f"SPN token failed: {e}")
        raise

# === ENDPOINT ===
@app.post("/normalize-uploaded")
async def normalize_uploaded(
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_any_user)
):
    try:
        testcase_id = payload.get("testcaseid")
        original_steps = payload.get("original_steps", [])

        if not testcase_id:
            raise HTTPException(status_code=400, detail="testcaseid is required")
        if not original_steps:
            raise HTTPException(status_code=400, detail="original_steps cannot be empty")

        # Input cleaning
        steps_input = []
        for i, step in enumerate(original_steps):
            idx = step.get("Index", i + 1)
            step_text = str(step.get("Step", "") or "").strip()
            data_text = str(step.get("TestDataText", "") or "").strip()
            steps_input.append({"Index": idx, "Step": step_text, "TestDataText": data_text})

        prompt = f"""You are an expert QA automation engineer.
Normalize the following test steps into clean, atomic, BDD-style format (Given/When/Then).

Rules:
1. Rewrite each Step clearly and action-oriented
2. Keep TestDataText as human-readable
3. Infer structured TestData JSON:
   - email + password → {{"username": "...", "password": "..."}}
   - URL → {{"url": "..."}}
   - single value → {{"value": "..."}}}
   - empty → {{}}
4. Return ONLY a valid JSON array. No markdown, no code blocks, no explanations.

Input:
{json.dumps(steps_input, indent=2)}

Output format:
[
  {{
    "Index": 1,
    "Step": "When the user enters valid credentials",
    "TestDataText": "user@example.com, pass123",
    "TestData": {{"username": "user@example.com", "password": "pass123"}}
  }}
]
"""

        # === GET TOKEN + CLIENT ===
        try:
            access_token = get_access_token()
        except:
            logging.warning("SPN failed, falling back to API key")
            access_token = AZURE_OPENAI_API_KEY  # fallback

        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            api_key=AZURE_OPENAI_API_KEY,  # always required
            default_headers={
                "Authorization": f"Bearer {access_token}",
                "user_sid": "NORMALIZE_USER"
            },
            timeout=300  # 5 min
        )

        # === CALL AZURE OPENAI ===
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=3000,
            top_p=0.9,
            timeout=300
        )

        raw_output = response.choices[0].message.content.strip()

        # Extract JSON
        start = raw_output.find("[")
        end = raw_output.rfind("]") + 1
        if start == -1 or end == 0:
            raise HTTPException(status_code=500, detail=f"AI did not return JSON: {raw_output[:200]}")

        try:
            normalized_data = json.loads(raw_output[start:end])
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON: {e}")

        # Final output
        normalized_steps = []
        for i, item in enumerate(normalized_data):
            test_data = item.get("TestData", {})
            if not isinstance(test_data, dict):
                test_data = {"value": str(test_data)} if test_data else {}
            normalized_steps.append({
                "Index": item.get("Index", i + 1),
                "Step": str(item.get("Step", "") or "").strip(),
                "TestDataText": str(item.get("TestDataText", "") or "").strip(),
                "TestData": test_data
            })

        return {
            "testcaseid": testcase_id,
            "original_steps_count": len(original_steps),
            "normalized_steps": normalized_steps,
            "message": "Test steps successfully normalized by Azure OpenAI",
            "model_used": AZURE_OPENAI_DEPLOYMENT,
            "auth_method": "SPN" if access_token != AZURE_OPENAI_API_KEY else "API Key"
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[NORMALIZE ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Normalization failed: {e}")
