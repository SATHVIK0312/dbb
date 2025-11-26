# ====================== AZURE OPENAI NORMALIZATION ENDPOINT ======================
@app.post("/normalize-uploaded")
async def normalize_uploaded(
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_any_user)
):
    """
    AI-powered test step normalization using Azure OpenAI
    Converts raw Excel steps → clean, structured, BDD-style steps
    """
    conn = None
    try:
        testcase_id = payload.get("testcaseid")
        original_steps = payload.get("original_steps", [])

        if not testcase_id:
            raise HTTPException(status_code=400, detail="testcaseid is required")
        if not original_steps:
            raise HTTPException(status_code=400, detail="original_steps cannot be empty")

        # Prepare clean input for AI
        steps_input = []
        for i, step in enumerate(original_steps):
            idx = step.get("Index", i + 1)
            step_text = str(step.get("Step", "") or "").strip()
            data_text = str(step.get("TestDataText", "") or "").strip()
            steps_input.append({
                "Index": idx,
                "Step": step_text,
                "TestDataText": data_text
            })

        prompt = f"""You are an expert QA automation engineer.

Normalize the following test steps into clean, atomic, BDD-style format (Given/When/Then).

Rules:
1. Rewrite each Step clearly and action-oriented
2. Keep TestDataText as human-readable
3. Infer structured TestData JSON:
   - email + password → {{"username": "...", "password": "..."}}
   - URL → {{"url": "..."}}
   - single value → {{"value": "..."}}
   - empty → {{}}
4. Return ONLY a valid JSON array. No markdown, no code blocks, no explanations.

Input:
{json.dumps(steps_input, indent=2)}

Output format (exact JSON array):
[
  {{
    "Index": 1,
    "Step": "When the user enters valid credentials and clicks login",
    "TestDataText": "user@example.com, pass123",
    "TestData": {{"username": "user@example.com", "password": "pass123"}}
  }}
]
"""

        # AZURE OPENAI CALL (using your existing client)
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,   # ← Correct for your setup
            messages=[
                {"role": "system", "content": "Return only valid JSON array. No extra text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=3000,
            top_p=0.9
        )

        raw_output = response.choices[0].message.content.strip()

        # Extract JSON array safely
        start = raw_output.find("[")
        end = raw_output.rfind("]") + 1
        if start == -1 or end == 0:
            raise HTTPException(
                status_code=500,
                detail=f"AI did not return valid JSON array. Response: {raw_output[:300]}"
            )

        try:
            normalized_data = json.loads(raw_output[start:end])
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON from AI: {e}")

        # Sanitize and validate output
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
            "normalized_steps_count": len(normalized_steps),
            "normalized_steps": normalized_steps,
            "message": "Test steps successfully normalized by Azure OpenAI",
            "model_used": AZURE_OPENAI_DEPLOYMENT,
            "processed_by": current_user["userid"]
        }

    except HTTPException:
        raise
    except Exception as e:
        error_detail = str(e)
        print(f"[NORMALIZE ERROR] User: {current_user['userid']} | Error: {error_detail}")
        raise HTTPException(
            status_code=500,
            detail=f"Normalization failed: {error_detail}"
        )
