# ------------------ Response Models ------------------
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import logging
from fastapi import Body, HTTPException

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
    model_used: str = "gpt-4o"  # will be overridden dynamically


# ------------------ MAIN ENDPOINT ------------------
@app.post("/generate-test-script/{testcase_id}", response_model=GeneratedScriptResponse)
async def generate_test_script(
    testcase_id: str,
    script_type: str = Body(..., example="playwright"),
    script_lang: str = Body(..., example="python"),
    include_prereq: bool = Body(False),
    testplan: Dict[str, Any] = Body(...),
):
    """
    Generate modular, reusable automation script + extract methods using Azure OpenAI (GPT-4o)
    Uses your existing get_azure_openai_client() → SPN + cert + fallback
    """
    try:
        script_type = script_type.lower()
        script_lang = script_lang.lower()

        if script_type not in ("playwright", "selenium"):
            raise HTTPException(400, "script_type must be 'playwright' or 'selenium'")
        if script_lang not in ("python", "java"):
            raise HTTPException(400, "script_lang must be 'python' or 'java'")

        prereq_text = ("Include prerequisite steps (browser launch, login, navigation, etc.)"
                       if include_prereq else "Skip all prerequisites. Start directly from the first test action.")

        prompt = f"""
You are an expert {script_type} automation engineer writing clean, modular {script_lang} code.

TEST CASE ID: {testcase_id}
FRAMEWORK: {script_type}
LANGUAGE: {script_lang}
{prereq_text}

TEST PLAN:
{json.dumps(testplan, indent=2, ensure_ascii=False)}

INSTRUCTIONS:
- Break down every logical action into a reusable method
- Put all reusable methods inside a class called `AutomationHelper`
- Write a main test function that orchestrates everything
- Use proper escaping: represent newlines in strings as \\n
- Return ONLY a valid JSON object with this exact structure:

{{
  "script": "<full executable script with \\n for line breaks>",
  "methods": [
    {{
      "method_name": "login_user",
      "class_name": "AutomationHelper",
      "intent": "Logs in user with credentials",
      "semantic_description": "Goes to login page, fills form, submits, waits for dashboard",
      "keywords": ["login", "auth", "signin"],
      "parameters": "page, username: str, password: str",
      "return_type": "None",
      "full_signature": "AutomationHelper.login_user(page, username, password)",
      "example": "helper.login_user(page, 'user@test.com', 'Pass123!')",
      "method_code": "def login_user(self, page, username: str, password: str):\\n    page.goto('https://app.com/login')\\n    ..."
    }}
  ]
}}

Do not include markdown, code fences, or explanations. Only the JSON.
"""

        # Use your existing, battle-tested client
        client = get_azure_openai_client()

        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},   # Forces valid JSON
            temperature=0.1,
            max_tokens=4000,
            top_p=0.95,
            timeout=300
        )

        raw_output = response.choices[0].message.content.strip()

        # Safe JSON parsing
        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError as e:
            logging.error(f"[GENERATE] Invalid JSON from model: {e}\nOutput: {raw_output[:1000]}")
            raise HTTPException(500, "AI returned invalid JSON format")

        script_raw = data.get("script", "")
        methods_raw = data.get("methods", [])

        if not script_raw:
            raise HTTPException(500, "Generated script is empty")

        # Convert \n → real newlines
        full_script = script_raw.replace("\\n", "\n").strip()

        # Extract reusable methods
        reusable_methods = []
        for m in methods_raw:
            method_code = m.get("method_code", "")
            if method_code and ("def " in method_code or "public " in method_code or "void " in method_code):
                clean_code = method_code.replace("\\n", "\n").strip()
                # Basic validation
                if clean_code.startswith(("def ", "public ", "private ", "protected ")):
                    reusable_methods.append(ReusableMethodResponse(
                        name=m.get("method_name", "unnamed_method"),
                        code=clean_code
                    ))

        model_used = response.model  # e.g., "gpt-4o-2024-08-06"

        return GeneratedScriptResponse(
            testcase_id=testcase_id,
            script_type=script_type,
            script_lang=script_lang,
            generated_script=full_script,
            reusable_methods=reusable_methods,
            saved_count=len(reusable_methods),
            model_used=model_used
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"[GENERATE] Failed for {testcase_id}: {e}")
        raise HTTPException(500, f"Script generation failed: {str(e)}")
