"""
MADL Data Models
Structures for MADL-related operations and storage.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class MADLMethodMetadata(BaseModel):
    """Metadata for a method to be stored in MADL"""
    method_name: str
    class_name: str
    file_path: str
    intent: str
    semantic_description: str
    keywords: List[str]
    parameters: str
    return_type: str
    full_signature: str
    example: str
    method_code: Optional[str] = None


class MADLSearchResult(BaseModel):
    """Result from MADL search"""
    method_name: str
    class_name: str
    file_path: str
    intent: str
    match_score: float
    match_percentage: float
    example: str
    keywords: List[str]


class ExecutionContext(BaseModel):
    """Context for execution with MADL"""
    testcase_id: str
    script_type: str
    test_plan: Dict[str, Any]
    selected_madl_methods: Optional[List[str]] = None
    user_id: str


class ExecutionResult(BaseModel):
    """Result of execution"""
    testcase_id: str
    status: str  # SUCCESS, FAILED
    execution_time_ms: float
    error_message: Optional[str] = None
    madl_stored: bool = False
    madl_method_name: Optional[str] = None
    output: str
