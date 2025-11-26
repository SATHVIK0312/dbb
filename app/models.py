from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime

# =============================================================================
# EXECUTION / LOGGING MODELS
# =============================================================================

class ExecutionLog(BaseModel):
    """
    Generic execution log entry used for streaming / structured logs.
    """
    timestamp: str = datetime.now().isoformat()
    message: str
    status: str  # "INFO", "RUNNING", "SUCCESS", "FAILED", "ERROR"


class ExecutionResponse(BaseModel):
    """
    High-level execution response. Used where we want to expose execution state.
    """
    testcaseid: str
    script_type: str  # "playwright" or "selenium"
    status: str       # "STARTED", "RUNNING", "COMPLETED", "FAILED"
    logs: List[ExecutionLog] = []


class TestScriptResponse(BaseModel):
    """
    Response when uploading / saving a test script.
    """
    testcaseid: str
    projectid: str
    message: str


# =============================================================================
# PROJECT & TEST CASE BASIC INFO (LIST / SUMMARY)
# =============================================================================

class ProjectInfo(BaseModel):
    """
    Lightweight project info used for listing / dropdowns.
    """
    projectid: str
    title: str
    startdate: date
    projecttype: str
    description: Optional[str]


class TestCaseInfo(BaseModel):
    """
    Summary of a test case (without steps) for listing.
    """
    testcaseid: str
    testdesc: str
    pretestid: Optional[str]
    prereq: Optional[str]
    tag: List[str]
    # In DB this is an array; in some places we treat it as list
    projectid: List[str]


class TestStepInfo(BaseModel):
    """
    Raw steps for a testcase from teststep table.
    """
    testcaseid: str
    steps: List[str]
    args: List[str]
    stepnum: int


# =============================================================================
# USER / AUTH / DASHBOARD MODELS
# =============================================================================

class UserCreate(BaseModel):
    """
    Input for user creation.
    """
    name: str
    mail: str
    password: str
    role: str  # "role-1", "role-2", ...


class UserResponse(BaseModel):
    """
    Basic user info returned after creation.
    """
    name: str
    mail: str
    userid: str
    role: str


class LoginCreate(BaseModel):
    """
    Login request body. 'username' maps to 'name' in DB.
    """
    username: str
    password: str


class ProjectResponse(BaseModel):
    """
    Project details used in multiple places (login payload, etc.).
    """
    projectid: str
    title: str
    startdate: date
    projecttype: str
    description: str


class LoginResponse(BaseModel):
    """
    Response for /login: JWT token + projects accessible to the user.
    """
    userid: str
    role: str
    token: str
    projects: List[ProjectResponse]


# ---------------- Dashboard Shapes ----------------

class StepResponse(BaseModel):
    """
    Steps and arguments for a testcase as embedded in dashboard structure.
    """
    steps: List[str]
    args: List[str]
    stepnum: int


class TestCaseWithSteps(BaseModel):
    """
    Test case plus its steps, used in /me dashboard response.
    """
    testcaseid: str
    testdesc: str
    pretestid: Optional[str]
    prereq: Optional[str]
    tag: List[str]
    # In DB this is varchar[]; treated as list here
    projectid: List[str]
    steps: StepResponse


class ProjectWithTestCases(BaseModel):
    """
    Project plus all of its test cases (with steps) for the dashboard.
    """
    projectid: str
    title: str
    startdate: date
    projecttype: str
    description: str
    testcases: List[TestCaseWithSteps]


class UserDashboardResponse(BaseModel):
    """
    Top-level shape for the /me dashboard endpoint.
    """
    userid: str
    role: str
    projects: List[ProjectWithTestCases]


# =============================================================================
# PROJECT / ASSIGNMENT MODELS
# =============================================================================

class ProjectCreate(BaseModel):
    """
    Input for creating a project.
    """
    title: str
    startdate: date
    projecttype: str
    description: str


class AssignmentCreate(BaseModel):
    """
    Input for assigning a user to one or more projects.
    """
    userid: str
    projectids: List[str]


class AssignmentResponse(BaseModel):
    """
    Response shape for a single assignment.
    """
    userid: str
    projectids: List[str]


class BulkAssignmentResponse(BaseModel):
    """
    Response for bulk assignment operations.
    """
    message: str
    assigned: List[AssignmentResponse]


# =============================================================================
# TEST CASE CREATION / UPDATE / RESPONSE
# =============================================================================

class TestCaseCreate(BaseModel):
    """
    Input for /testcase/ creation.
    Note: projectid is a single project ID (your choice = B).
    """
    testdesc: str
    pretestid: Optional[str] = None
    prereq: Optional[str] = None
    tag: List[str]
    projectid: str  # single projectid in request; DB may still store as array


class TestStepResponse(BaseModel):
    """
    Basic step payload used in some responses.
    """
    testcaseid: str
    steps: List[str]
    args: List[str]
    stepnum: int


class BulkTestCaseResponse(BaseModel):
    """
    Response for a single testcase during bulk operations.
    """
    testcaseid: str
    message: str
    steps_saved: int


class BulkUploadResponse(BaseModel):
    """
    Final summary of bulk Excel upload (/upload-testcases).
    """
    message: str
    testcases_created: int
    total_steps: int


class TestCaseResponse(BaseModel):
    """
    Canonical testcase response.
    - Used by /testcase/ (create) and /replace-normalized/{testcase_id}
    - Must be compatible with both:
        * Sometimes projectid is a single string (create)
        * Sometimes it's a list from DB (replace-normalized)
    """
    testcaseid: str
    testdesc: Optional[str] = None
    pretestid: Optional[str] = None
    prereq: Optional[str] = None
    tag: List[str]
    # Accept either single projectid or list of projectids
    projectid: Union[str, List[str]]
    # Optional extra field if you later want to embed steps
    # (kept optional so existing endpoints work without passing it)
    # steps: Optional[StepResponse] = None


class TestPlanStep(BaseModel):
    """
    One step in a generated test plan.
    """
    step_desc: str
    step_args: str


class TestPlanResponse(BaseModel):
    """
    Response wrapper for a generated test plan.
    """
    testcaseid: str
    testdesc: str
    steps: List[TestPlanStep]


class TestCaseUpdate(BaseModel):
    """
    Payload for partial testcase update (PATCH-like semantics).
    """
    testdesc: Optional[str] = None
    pretestid: Optional[str] = None
    prereq: Optional[str] = None
    tag: Optional[List[str]] = None


# =============================================================================
# BDD / DETAILED TESTCASE STRUCTURES (for WPF client, etc.)
# =============================================================================

class Step(BaseModel):
    """
    Rich step model used for:
    - Normalization (Gemini)
    - Detailed test case view in WPF
    """
    Index: int
    Step: str
    TestDataText: str
    TestData: Dict[str, Any]


class Prerequisite(BaseModel):
    """
    One prerequisite test case reference in the detailed view.
    """
    PrerequisiteID: str
    Description: str


class Scenario(BaseModel):
    """
    One scenario inside TestCaseDetails, used by the desktop client.
    """
    ScenarioId: str
    Description: str
    Prerequisites: List[Prerequisite]
    IsBdd: bool
    Status: str
    Steps: List[Step]


class TestCaseDetails(BaseModel):
    """
    Root object returned to the WPF UI describing a test case in detail.
    """
    Scenarios: List[Scenario]


# =============================================================================
# EXCEL UPLOAD / NORMALIZATION / STAGING MODELS
# =============================================================================

class NormalizeResponse(BaseModel):
    """
    Response for /normalize-teststeps (or similar) – wraps original and normalized.
    """
    testcaseid: str
    original_steps: List[Step]
    normalized_steps: List[Step]
    message: str


class NormalizedStep(BaseModel):
    """
    One normalized step as returned by Gemini and posted back.
    """
    Index: Optional[int] = None
    Step: str
    TestDataText: Optional[str] = None
    TestData: Optional[Dict[str, Any]] = None


class NormalizedStepsUpdate(BaseModel):
    """
    Request body for /replace-normalized/{testcase_id}.
    """
    normalized_steps: List[NormalizedStep]


class ExcelUploadTestCase(BaseModel):
    """
    One row group from Excel after preprocessing.
    """
    testcase_id: Optional[str] = None
    test_case_description: str
    pre_requisite_test_id: Optional[str] = None
    pre_requisite_description: Optional[str] = None
    tags: str              # comma or semicolon separated
    test_steps: str        # newline separated
    arguments: str         # newline separated
    project_id: str        # comma or semicolon separated


class ExcelUploadData(BaseModel):
    """
    Body for /stage-excel-upload – list of test cases from Excel.
    """
    testcases: List[ExcelUploadTestCase]


class StagedTestCase(BaseModel):
    """
    Staged testcase structure used internally; response currently returns list[dict]
    but we keep a model here for clarity / future typing.
    """
    testcaseid: str
    testdesc: str
    pretestid: Optional[str]
    prereq: Optional[str]
    tags: List[str]
    projectids: List[str]
    steps: List[Dict[str, Any]]


class StageUploadResponse(BaseModel):
    """
    Response for /stage-excel-upload.
    """
    message: str
    testcases_count: int
    staged_testcases: List[Dict[str, Any]]


class CommitUploadData(BaseModel):
    """
    Request body for /commit-staged-upload.
    User selects a single project, and passes staged testcases.
    """
    projectid: str                  # Single project selected by user
    testcases: List[Dict[str, Any]]


class CommitUploadResponse(BaseModel):
    """
    Response for /commit-staged-upload.
    """
    message: str
    testcases_committed: int


class PaginatedTestCaseResponse(BaseModel):
    """
    One testcase row in paginated list.
    """
    testcaseid: str
    testdesc: str
    pretestid: Optional[str]
    prereq: Optional[str]
    tag: List[str]
    projectid: List[str]
    steps_count: int


class PaginatedTestCasesResponse(BaseModel):
    """
    Wrapper for paginated testcase list.
    """
    page: int
    page_size: int
    total_count: int
    total_pages: int
    testcases: List[PaginatedTestCaseResponse]
    message: str
