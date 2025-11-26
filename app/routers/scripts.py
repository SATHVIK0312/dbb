from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import logging

from azure_openai_client import call_openai_api
import config
import models
import utils
import database as db
from routers.users import get_current_any_user



# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/generate-test-script/{testcase_id}")
async def generate_test_script(testcase_id: str, script_type: str, script_lang: str, testplan: dict):
    try:
        # Validate inputs
        if script_type.lower() not in ["playwright", "selenium"]:
            raise HTTPException(status_code=400, detail="Invalid script_type. Use 'playwright' or 'selenium'")
        if script_lang.lower() not in ["python", "java"]:
            raise HTTPException(status_code=400, detail="Invalid script_lang. Use 'python' or 'java'")

        # Prepare prompt for Azure OpenAI API
        prompt = f"Generate a test script for test case ID: {testcase_id}\n"
        prompt += f"Script type: {script_type}, Language: {script_lang}\n"
        prompt += "Test plan JSON: " + json.dumps(testplan) + "\n"
        prompt += "Requirements:\n"
        prompt += "- Include comments above each action describing the step.\n"
        prompt += "- Don't use pytest\n"
        prompt += "- Wrap each action in a try-catch block.\n"
        prompt += "- Add print statements with timestamps before and after each action (e.g., 'Running action: <step> at <timestamp>' and 'Action runned: <step> at <timestamp>').\n"
        prompt += "- If an action fails, print 'Action <step> failed at <timestamp> due to: <error>'.\n"
        prompt += "- Use appropriate imports and syntax for the chosen script type and language.\n"
        prompt += "- Handle actions: 'Navigate to login', 'Enter credentials', 'Submit form' (assume credentials are in 'user/pass' format, split by '/').\n"
        prompt += "- Output only the code, no additional explanations or markdown (e.g., no ''' or # comments outside actions).\n"

        script_content = call_openai_api(
            prompt=prompt,
            max_tokens=4000,
            system_message="You are a test automation expert. Generate only executable Python code."
        )

        # Validate generated content
        if not script_content:
            raise HTTPException(status_code=500, detail="Failed to generate script content")

        # Determine file extension
        file_extension = ".py" if script_lang.lower() == "python" else ".java"
        filename = f"{testcase_id}_script{file_extension}"

        # Return as downloadable file using StreamingResponse
        return StreamingResponse(
            iter([script_content.encode("utf-8")]),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Script generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")
