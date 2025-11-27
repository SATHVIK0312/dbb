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
2. Restructure the step numbers / index numbers if they are wrong or non sequential, make them sequential and make sure it starts from 1
3. Keep TestDataText as human-readable
4. Infer structured TestData JSON:
   - email + password → {{"username": "...", "password": "..."}}
   - URL → {{"url": "..."}}
   - single value → {{"value": "..."}}}
   - empty → {{}}
5. Return ONLY a valid JSON array. No markdown, no code blocks.
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

        client = get_azure_openai_client()
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=3000,
            top_p=0.9,
            timeout=300
        )

        raw_output = response.choices[0].message.content.strip()
        start = raw_output.find("[")
        end = raw_output.rfind("]") + 1
        if start == -1 or end == 0:
            raise HTTPException(status_code=500, detail=f"Invalid AI output: {raw_output[:200]}")

        try:
            normalized_data = json.loads(raw_output[start:end])
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON: {e}")

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

        # CRITICAL: Include original steps in response!
        return {
            "testcaseid": testcase_id,
            "original": original_steps,        # This was missing!
            "normalized": normalized_steps,    # This was already there
            "original_steps_count": len(original_steps),
            "normalized_steps_count": len(normalized_steps),
            "message": "Normalization completed successfully",
            "model_used": AZURE_OPENAI_DEPLOYMENT
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[NORMALIZE ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Normalization failed: {e}")
