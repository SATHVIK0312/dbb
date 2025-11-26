"""
MADL Storage Service
Extracts successful test execution patterns and stores them to vector DB for future reuse.
"""

from typing import List, Dict, Any, Optional

from routers.madl_integration import madl_client
from routers.structured_logging import StructuredLog, LogCategory
import utils
import config

from azure_openai_client import call_openai_api


async def extract_madl_metadata_from_script(
    testcase_id: str,
    generated_script: str,
    test_plan: Dict[str, Any],
    execution_logs: List[StructuredLog]
) -> Optional[Dict[str, Any]]:
    """
    Extract MADL metadata from a successful script execution.
    Uses Azure OpenAI to analyze the script and identify reusable components.
    """
    try:
        # Collect successful actions from logs
        successful_actions = []
        for log in execution_logs:
            if log.level == "SUCCESS" and log.category == "EXECUTION":
                if log.code:
                    successful_actions.append({
                        "action": log.code,
                        "message": log.message,
                        "details": log.details
                    })
        
        analysis_prompt = f"""
        Analyze this successful test script and identify reusable methods/components.
        
        TEST CASE ID: {testcase_id}
        
        SCRIPT:
        {generated_script}
        
        SUCCESSFUL ACTIONS:
        {successful_actions}
        
        TEST PLAN:
        {test_plan}
        
        Please extract:
        1. Method Name: What would be a good name for this reusable method?
        2. Intent: What is the high-level purpose?
        3. Keywords: Important keywords (list 5-10)
        4. Semantic Description: Detailed description of what this method does
        5. Parameters: Extracted parameters (if any)
        6. Return Type: What does it return?
        7. Example: Usage example
        
        Format as JSON:
        {{
            "method_name": "...",
            "intent": "...",
            "keywords": [...],
            "semantic_description": "...",
            "parameters": "...",
            "return_type": "...",
            "example": "...",
            "class_name": "AutomationHelper",
            "file_path": "generated_methods.py"
        }}
        """
        
        response = call_openai_api(
            prompt=analysis_prompt,
            max_tokens=1500,
            system_message="You are a test automation expert. Extract metadata and return only valid JSON."
        )
        
        # Parse Azure OpenAI response
        import json
        import re
        
        response_text = response
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            metadata = json.loads(json_match.group())
            utils.logger.info(f"[MADL] Extracted metadata: {metadata.get('method_name')}")
            return metadata
        else:
            utils.logger.warning("[MADL] No JSON found in Azure OpenAI response")
            return None
    
    except Exception as e:
        utils.logger.error(f"[MADL] Metadata extraction failed: {str(e)}")
        return None


async def store_successful_execution_to_madl(
    testcase_id: str,
    generated_script: str,
    test_plan: Dict[str, Any],
    execution_logs: List[StructuredLog],
    execution_output: str
) -> bool:
    """
    Store a successful test execution as a reusable method in MADL vector DB.
    """
    try:
        utils.logger.info(f"[MADL] Starting storage process for {testcase_id}")
        
        # Extract metadata from the successful script
        metadata = await extract_madl_metadata_from_script(
            testcase_id=testcase_id,
            generated_script=generated_script,
            test_plan=test_plan,
            execution_logs=execution_logs
        )
        
        if not metadata:
            utils.logger.warning("[MADL] No metadata extracted, skipping storage")
            return False
        
        # Store to vector DB
        success = await madl_client.store_method(
            method_name=metadata.get("method_name", f"auto_{testcase_id}"),
            class_name=metadata.get("class_name", "AutomationHelper"),
            file_path=metadata.get("file_path", "generated_methods.py"),
            intent=metadata.get("intent", ""),
            semantic_description=metadata.get("semantic_description", ""),
            keywords=metadata.get("keywords", []),
            parameters=metadata.get("parameters", ""),
            return_type=metadata.get("return_type", ""),
            full_signature=f"{metadata.get('class_name', 'AutomationHelper')}.{metadata.get('method_name', f'auto_{testcase_id}')}()",
            example=metadata.get("example", ""),
            method_code=generated_script
        )
        
        if success:
            utils.logger.info(f"[MADL] Successfully stored method for {testcase_id}")
            return True
        else:
            utils.logger.error(f"[MADL] Failed to store method for {testcase_id}")
            return False
    
    except Exception as e:
        utils.logger.error(f"[MADL] Storage failed: {str(e)}")
        return False
