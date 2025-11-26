import io
import json
import pandas as pd

from fastapi import APIRouter, UploadFile, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from azure_openai_client import call_openai_api
import config

from routers.users import get_current_any_user
from app import models
from app import utils
from app import database as db
from app.routers.users import get_current_any_user


router = APIRouter()

# Store the last normalized output in app state
_last_output = None

# ==========================================================
# 🧩 HELPER: Azure OpenAI Normalization Function
# ==========================================================
def normalize_with_llm(steps):
    """
    Takes a list of test steps and sends them to the Azure OpenAI LLM
    to normalize them into atomic BDD-style steps.
    """
    prompt = f"""
You are a QA automation expert.
You are given a list of test steps in JSON. Some steps combine multiple actions.
Normalize them so that:
- Each step performs exactly one action.
- Each step has correctly mapped test data.
- Use clean BDD style (Given/When/Then/And).
Return JSON array with keys: Index, Step, TestDataText, TestData.

Example:
Input:
[
  {{
    "Index": 2,
    "Step": "When I enter username and password then click login",
    "TestData": {{
      "username": "locked.user@corp",
      "password": "wrongpass"
    }}
  }}
]

Output:
[
  {{
    "Index": 1,
    "Step": "When I enter username",
    "TestDataText": "username:locked.user@corp",
    "TestData": {{"username": "locked.user@corp"}}
  }},
  {{
    "Index": 2,
    "Step": "And I enter password",
    "TestDataText": "password:wrongpass",
    "TestData": {{"password": "wrongpass"}}
  }},
  {{
    "Index": 3,
    "Step": "And I click login",
    "TestDataText": "",
    "TestData": {{}}
  }}
]

Now normalize:
{json.dumps(steps, indent=2)}
Return ONLY the JSON array.
"""
    try:
        text = call_openai_api(
            prompt=prompt,
            max_tokens=2000,
            system_message="You are a QA automation expert. Return only valid JSON arrays."
        )

        # Extract JSON content from response
        start = text.find("[")
        end = text.rfind("]") + 1
        normalized = json.loads(text[start:end])
        return normalized
    except Exception as e:
        print(f"❌ Azure OpenAI normalization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Normalization failed: {str(e)}")


# ==========================================================
# 🚀 ENDPOINTS
# ==========================================================

@router.post("/normalize")
async def normalize_endpoint(file: UploadFile, current_user = Depends(get_current_any_user)):
    """
    Accepts a JSON file, normalizes the test steps using Azure OpenAI,
    and returns an HTML table comparison of original vs normalized steps.
    Added authentication via get_current_any_user
    """
    global _last_output
    
    try:
        # Read file contents
        file_bytes = await file.read()
        data = json.loads(file_bytes.decode("utf-8"))
    except Exception as e:
        return HTMLResponse(f"<h3>❌ Invalid JSON file. Error: {str(e)}</h3>", status_code=400)

    # Validate JSON structure
    scenarios = data.get("Scenarios", [])
    if not scenarios:
        return HTMLResponse("<h3>❌ No 'Scenarios' key found in the JSON.</h3>", status_code=400)

    scenario = scenarios[0]
    original_steps = scenario.get("Steps", [])
    if not original_steps:
        return HTMLResponse("<h3>❌ No 'Steps' found in the scenario.</h3>", status_code=400)

    # Normalize steps using LLM
    normalized_steps = normalize_with_llm(original_steps)

    # Prepare new output JSON
    output_json = data.copy()
    output_json["Scenarios"][0]["Steps"] = normalized_steps
    output_bytes = io.BytesIO(json.dumps(output_json, indent=2, ensure_ascii=False).encode("utf-8"))

    # Store output for download
    _last_output = output_bytes

    # Convert to dataframes for display
    df_orig = pd.DataFrame([
        {"Step No.": s["Index"], "Step": s["Step"], "Test Data": s.get("TestDataText", "")}
        for s in original_steps
    ])
    df_norm = pd.DataFrame([
        {"Step No.": s["Index"], "Step": s["Step"], "Test Data": s.get("TestDataText", "")}
        for s in normalized_steps
    ])

    orig_html = df_orig.to_html(index=False, classes="table table-dark", justify="center")
    norm_html = df_norm.to_html(index=False, classes="table table-success", justify="center")

    download_link = (
        '<a href="/download_normalized" '
        'style="font-size:16px; background:#007bff; color:white; padding:8px 12px; '
        'text-decoration:none; border-radius:6px;">⬇ Download Normalized JSON</a>'
    )

    html = f"""
    <html>
    <head>
      <title>Normalized Test Steps</title>
      <style>
        body {{
          background-color: #111;
          color: #eee;
          font-family: Arial, sans-serif;
          padding: 30px;
        }}
        .table {{
          width: 80%;
          margin: 20px auto;
          border-collapse: collapse;
          border: 1px solid #444;
        }}
        th, td {{
          border: 1px solid #444;
          padding: 10px;
          text-align: center;
        }}
        h2 {{
          color: #ffd700;
          text-align: center;
        }}
        a:hover {{
          background-color: #0056b3;
        }}
      </style>
    </head>
    <body>
      <h2>Original Steps</h2>
      {orig_html}
      <h2>Normalized Steps</h2>
      {norm_html}
      <div style="text-align:center; margin-top:30px;">
        {download_link}
      </div>
    </body>
    </html>
    """
    return HTMLResponse(html)


@router.get("/download_normalized")
async def download_normalized(current_user = Depends(get_current_any_user)):
    """
    Allows the user to download the last normalized JSON output.
    Added authentication via get_current_any_user
    """
    global _last_output
    
    if _last_output is None:
        return HTMLResponse("<h3>No normalized file generated yet.</h3>", status_code=404)
    
    _last_output.seek(0)
    return StreamingResponse(
        _last_output,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=normalized_output.json"},
    )
