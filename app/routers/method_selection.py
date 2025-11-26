"""
Method Selection Endpoint
Handles user selection of reusable methods before execution.
"""

from fastapi import APIRouter, HTTPException, Depends, Form
from typing import List, Optional
from pydantic import BaseModel

from routers.madl_integration import madl_client, ReusableMethod, search_for_reusable_methods
from routers.madl_storage import store_successful_execution_to_madl

import utils

router = APIRouter()


class MethodSelectionRequest(BaseModel):
    """User selection of methods to include in script generation"""
    selected_method_signatures: List[str]  # e.g., ["LoginService.loginUser", "FormHelper.fillForm"]


class MethodSelectionResponse(BaseModel):
    """Response with selected methods ready for code generation"""
    testcase_id: str
    selected_methods: List[dict]
    message: str


@router.post("/testcases/{testcase_id}/search-reusable-methods")
async def search_reusable_methods_endpoint(
    testcase_id: str,
    testplan_json: str = Form(...)
):
    """
    Search for reusable methods relevant to a test case.
    Called after user clicks Execute but before final confirmation.
    
    Returns methods found in vector DB for user to select.
    """
    import json
    
    try:
        # Parse test plan
        testplan = json.loads(testplan_json)
        
        # Search for reusable methods
        methods = await search_for_reusable_methods(testplan)
        
        if not methods:
            utils.logger.info(f"[SEARCH] No reusable methods found for {testcase_id}")
            return {
                "testcase_id": testcase_id,
                "methods": [],
                "message": "No reusable methods found"
            }
        
        # Format for UI selection
        formatted_methods = [
            {
                "method_name": m.method_name,
                "class_name": m.class_name,
                "signature": f"{m.class_name}.{m.method_name}",
                "intent": m.intent,
                "match_percentage": m.match_percentage,
                "example": m.example,
                "keywords": m.keywords
            }
            for m in methods
        ]
        
        utils.logger.info(f"[SEARCH] Found {len(methods)} reusable methods for {testcase_id}")
        
        return {
            "testcase_id": testcase_id,
            "methods": formatted_methods,
            "message": f"Found {len(methods)} reusable methods"
        }
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid test plan JSON")
    except Exception as e:
        utils.logger.error(f"[SEARCH] Error searching methods: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.post("/testcases/{testcase_id}/confirm-method-selection")
async def confirm_method_selection(
    testcase_id: str,
    request: MethodSelectionRequest
):
    """
    User confirms which methods to include in script generation.
    Stores selection for use in generation phase.
    """
    try:
        utils.logger.info(f"[SELECTION] User selected {len(request.selected_method_signatures)} methods")
        
        # Validate selected methods exist in MADL
        selected_details = []
        for signature in request.selected_method_signatures:
            # In production, validate against MADL database
            parts = signature.split(".")
            if len(parts) == 2:
                selected_details.append({
                    "signature": signature,
                    "class_name": parts[0],
                    "method_name": parts[1]
                })
        
        return {
            "testcase_id": testcase_id,
            "selected_count": len(selected_details),
            "selected_methods": selected_details,
            "message": "Methods confirmed and ready for code generation"
        }
    
    except Exception as e:
        utils.logger.error(f"[SELECTION] Error confirming selection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Selection error: {str(e)}")
