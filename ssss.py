# app/main.py  (or wherever your FastAPI app instance lives)

from fastapi import FastAPI, HTTPException, Body, Depends
from typing import Dict, Any, List, Optional
import json
import logging

from app.utils import get_azure_openai_client
from app import config

app = FastAPI()

# Reuse your existing Azure OpenAI client
client = get_azure_openai_client()


# ------------------ Response Models ------------------
from pydantic import BaseModel

class ReusableMethodResponse(BaseModel):
    name: str
    code: str
    saved_to_db: bool = False

class GeneratedScriptResponse(BaseModel):
    testcase_id: str
    script_type: str
    script_lang: str
    generated_script: str
    reusable_methods: List[ReusableMethodResponse]
    saved_count: int = 0
    model_used: str = config.AZURE_OPENAI_DEPLOYMENT


# ------------------ MAIN ENDPOINT (using app.post directly) ------------------
@app.post("/generate-test-script/{testcase_id}", response_model=GeneratedScriptResponse)
async def generate_test_script(
    testcase_id: str,
    script_type: str = Body(..., example="playwright"),
    script_lang: str = Body(..., example="python"),
    include_prereq: bool = Body(False),
    testplan: Dict[str, Any] = Body(...),
):
    """
    Generate modular automation script + extract reusable methods using Azure OpenAI (GPT-4o)
    """
    try:
        script_type = script_type.lower()
        script_lang = script_lang.lower()

        if script_type not in ("playwright", "selenium"):
            raise HTTPException(400, "script_type must be 'playwright' or 'selenium'")
        if script_lang not in ("python", "java"):
            raise HTTPException(400, "script_lang must be 'python' or 'java'")

        prereq_text = "Include prerequisite steps (browser launch, login, etc.)" if include_prereq else "Skip all prerequisites. Start from the first test action."

        prompt = f"""
You are an expert {script_type} automation engineer.

Generate a complete, clean, modular {script_lang} test script and extract all reusable methods with full metadata.

TEST CASE ID: {testcase_id}
FRAMEWORK: {script_type}
LANGUAGE: {script_lang}
{prereq_text}

TEST PLAN:
{json.dumps(testplan, indent=2, ensure_ascii=False)}

RULES:
- Make every logical action a reusable method
- Put reusable methods in a class called AutomationHelper
- Include a main test function that runs everything
- Escape newlines properly in strings using \\n

Return ONLY valid JSON with this exact structure:
{{
  "script": "<full script with \\n for newlines>",
  "methods": [
    {{
      "method_name": "login_user",
      "class_name": "AutomationHelper",
      "intent": "Perform login with given credentials",
      "semantic_description": "Navigates to login page, fills username/password, submits and waits for dashboard",
      "keywords": ["login", "auth", "signin", "credentials"],
      "parameters": "page, username, password",
      "return_type": "None",
      "full_signature": "AutomationHelper.login_user(page, username, password)",
      "example": "helper.login_user(page, 'user@test.com', 'Pass123!')",
      "method_code": "def login_user(self, page, username: str, password: str):\\n    page.goto(..."
    }}
  ]
}}
"""

        response = client.chat.completions.create(
            model=config.AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},   # This guarantees perfect JSON
            temperature=0.1,
            max_tokens=4000,
            top_p=0.95,
        )

        raw_output = response.choices[0].message.content.strip()

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError as e:
            logging.error(f"JSON parse failed: {e}\nOutput: {raw_output[:1000]}")
            raise HTTPException(500, "Model returned invalid JSON")

        script = data.get("script", "").replace("\\n", "\n").strip()
        methods_raw = data.get("methods", [])

        if not script:
            raise HTTPException(500, "Generated script is empty")

        reusable_methods = []
        for m in methods_raw:
            code = m.get("method_code", "")
            if code and ("def " in code or "public " in code or "void " in code):
                clean_code = code.replace("\\n", "\n").strip()
                if clean_code.startswith("def ") or clean_code.startswith("public "):
                    reusable_methods.append(ReusableMethodResponse(
                        name=m.get("method_name", "unnamed_method"),
                        code=clean_code
                    ))

        return GeneratedScriptResponse(
            testcase_id=testcase_id,
            script_type=script_type,
            script_lang=script_lang,
            generated_script=script,
            reusable_methods=reusable_methods,
            saved_count=len(reusable_methods),
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Script generation failed for {testcase_id}")
        raise HTTPException(500, f"Generation failed: {str(e)}")
