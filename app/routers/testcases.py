from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from typing import List, Dict, Any

import pandas as pd
import io
import json
import logging
import traceback
import config
import models
import utils
import database as db
from routers.users import get_current_any_user

from azure_openai_client import call_openai_api

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/testcase/", response_model=models.TestCaseResponse,
             summary="Create a new testcase (requires login + project assignment)")
async def create_testcase(
        testcase: models.TestCaseCreate,
        current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        user_proj_row = await conn.fetchrow(
            'SELECT projectid FROM projectuser WHERE userid = $1',
            userid
        )
        if not user_proj_row:
            raise HTTPException(status_code=403,
                                detail="You are not assigned to any project")

        # `projectid` column is an array → check if requested project is in allowed list
        allowed_projects = set(user_proj_row["projectid"])
        if testcase.projectid not in allowed_projects:
            raise HTTPException(
                status_code=403,
                detail=f"You are not assigned to project {testcase.projectid}"
            )

        # Generate next TCxxxx id
        next_tid = await utils.get_next_testcaseid(conn)

        await conn.execute(
            """
            INSERT INTO testcase
              (testcaseid, testdesc, pretestid, prereq, tag, projectid)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            next_tid,
            testcase.testdesc,
            testcase.pretestid or None,
            testcase.prereq or None,
            testcase.tag,  # Still a list → varchar[]
            testcase.projectid  # Single string project_id
        )

        return models.TestCaseResponse(
            testcaseid=next_tid,
            testdesc=testcase.testdesc,
            pretestid=testcase.pretestid,
            prereq=testcase.prereq,
            tag=testcase.tag,
            projectid=testcase.projectid,  # Single string
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        if conn:
            await conn.close()


@router.post("/upload-testcases/", response_model=models.BulkUploadResponse)
async def upload_testcases_excel(
        file: UploadFile = File(...),
        current_user: dict = Depends(get_current_any_user)
):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Only .xlsx files are allowed")

    # Read Excel
    content = await file.read()
    df = pd.read_excel(io.BytesIO(content))

    # Required columns
    required = [
        "Test Case ID", "Test Case Description", "Prerequisite Test ID",
        "Prerequisite", "Tags", "Step", "Argument", "Project ID"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(missing)}")

    # Clean data
    df = df.replace({pd.NA: None, float('nan'): None})
    df["Test Case ID"] = df["Test Case ID"].astype(str).str.strip()
    df["Test Case ID"] = df["Test Case ID"].replace({"nan": None})

    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Get allowed projects
        user_proj = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1", userid
        )
        if not user_proj:
            raise HTTPException(status_code=403, detail="Not assigned to any project")
        allowed_projects = set(user_proj["projectid"])

        created = 0
        total_steps = 0

        # State tracking
        current_tc_id: str = None
        tc_data: Dict[str, Any] = {}
        steps: List[str] = []
        args: List[str] = []

        for idx, row in df.iterrows():
            raw_tc_id = row["Test Case ID"]
            tc_id = raw_tc_id if raw_tc_id and raw_tc_id not in ("", "nan", "None") else None

            # --- NEW TEST CASE STARTS ---
            if tc_id and tc_id != current_tc_id:
                # Save previous test case
                if current_tc_id:
                    await utils._save_testcase_and_steps(
                        conn=conn,
                        tc_id=current_tc_id,
                        data=tc_data,
                        steps=steps,
                        args=args,
                        allowed_projects=allowed_projects
                    )
                    created += 1
                    total_steps += len(steps)

                # Start new test case
                current_tc_id = tc_id
                tc_data = {
                    "desc": str(row["Test Case Description"] or "").strip(),
                    "pretestid": str(row["Prerequisite Test ID"] or "").strip() or None,
                    "prereq": str(row["Prerequisite"] or "").strip() or None,
                    "tags_raw": str(row["Tags"] or ""),
                    "proj_raw": str(row["Project ID"] or "")
                }
                steps = []
                args = []

            # --- ALWAYS collect step + argument ---
            step = str(row["Step"] or "").strip()
            arg = str(row["Argument"] or "").strip()
            if step:  # only add if step is not empty
                steps.append(step)
                args.append(arg)

        # --- SAVE FINAL TEST CASE ---
        if current_tc_id:
            await utils._save_testcase_and_steps(
                conn=conn,
                tc_id=current_tc_id,
                data=tc_data,
                steps=steps,
                args=args,
                allowed_projects=allowed_projects
            )
            created += 1
            total_steps += len(steps)

        return models.BulkUploadResponse(
            message="Upload successful",
            testcases_created=created,
            total_steps=total_steps
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.get("/projects/{project_id}/testcases", response_model=List[models.TestCaseInfo],
            summary="Get all test cases in a specific project (user must be assigned)")
async def get_testcases_in_project(
        project_id: str,
        current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # 1. Verify user has access to this project
        access = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1 AND $2 = ANY(projectid)",
            userid, project_id
        )
        if not access:
            raise HTTPException(status_code=403, detail="You are not assigned to this project")

        # 2. Fetch test cases
        testcases = await conn.fetch(
            """
            SELECT testcaseid, testdesc, pretestid, prereq, tag, projectid
            FROM testcase
            WHERE $1 = ANY(projectid)
            ORDER BY testcaseid
            """,
            project_id
        )

        return [
            models.TestCaseInfo(
                testcaseid=tc["testcaseid"],
                testdesc=tc["testdesc"],
                pretestid=tc["pretestid"],
                prereq=tc["prereq"],
                tag=tc["tag"],
                projectid=tc["projectid"]
            )
            for tc in testcases
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching test cases: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.get("/projects/{project_id}/testcases/paginated", response_model=models.PaginatedTestCasesResponse,
            summary="Get paginated test cases in a project")
async def get_testcases_paginated(
        project_id: str,
        page: int = 1,
        page_size: int = 10,
        current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Verify user has access to this project
        access = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1 AND $2 = ANY(projectid)",
            userid, project_id
        )
        if not access:
            raise HTTPException(status_code=403, detail="You are not assigned to this project")

        # Get total count
        total_count_row = await conn.fetchval(
            """
            SELECT COUNT(*) FROM testcase
            WHERE $1 = ANY(projectid)
            """,
            project_id
        )
        total_count = total_count_row or 0
        total_pages = (total_count + page_size - 1) // page_size

        # Calculate offset
        offset = (page - 1) * page_size

        # Fetch paginated testcases
        testcases = await conn.fetch(
            """
            SELECT testcaseid, testdesc, pretestid, prereq, tag, projectid
            FROM testcase
            WHERE $1 = ANY(projectid)
            ORDER BY testcaseid
            LIMIT $2 OFFSET $3
            """,
            project_id, page_size, offset
        )

        # Get step counts for each testcase
        result_testcases = []
        for tc in testcases:
            steps_count_row = await conn.fetchval(
                "SELECT COUNT(*) FROM teststep WHERE testcaseid = $1",
                tc["testcaseid"]
            )
            result_testcases.append(
                models.PaginatedTestCaseResponse(
                    testcaseid=tc["testcaseid"],
                    testdesc=tc["testdesc"],
                    pretestid=tc["pretestid"],
                    prereq=tc["prereq"],
                    tag=tc["tag"],
                    projectid=tc["projectid"],
                    steps_count=steps_count_row or 0
                )
            )

        return models.PaginatedTestCasesResponse(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            testcases=result_testcases,
            message="Testcases retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching test cases: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.get("/testcases/{testcase_id}/steps", response_model=models.TestStepInfo,
            summary="Get steps and arguments for a specific test case (user must have project access)")
async def get_testcase_steps(
        testcase_id: str,
        current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # 1. Get test case + its project(s)
        tc = await conn.fetchrow(
            """
            SELECT projectid FROM testcase WHERE testcaseid = $1
            """,
            testcase_id
        )
        if not tc:
            raise HTTPException(status_code=404, detail="Test case not found")

        # 2. Check if user has access to ANY of the projects
        user_access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = $1 AND projectid && $2",
            userid, tc["projectid"]
        )
        if not user_access:
            raise HTTPException(status_code=403, detail="You don't have access to this test case")

        # 3. Fetch steps
        steps_row = await conn.fetchrow(
            "SELECT steps, args, stepnum FROM teststep WHERE testcaseid = $1",
            testcase_id
        )
        if not steps_row:
            raise HTTPException(status_code=404, detail="Steps not found for this test case")

        return models.TestStepInfo(
            testcaseid=testcase_id,
            steps=steps_row["steps"],
            args=steps_row["args"],
            stepnum=steps_row["stepnum"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching steps: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.post("/testscripts/upload", response_model=models.TestScriptResponse,
             summary="Upload a Python script for a test case (requires authorization)")
async def upload_test_script(
        testcaseid: str = Form(...),  # Get testcaseid from form data
        scriptfile: UploadFile = File(..., description="Python script (.py) file"),
        current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # 1. Validate file type
        if not scriptfile.filename.endswith('.py'):
            raise HTTPException(status_code=400, detail="Only .py files are allowed")

        # 2. Read script content
        script_content = await scriptfile.read()
        script_text = script_content.decode('utf-8')  # Preserve indentation

        # 3. Fetch projectid from testcase
        tc_project = await conn.fetchrow(
            "SELECT projectid FROM testcase WHERE testcaseid = $1",
            testcaseid
        )
        if not tc_project:
            raise HTTPException(status_code=404, detail="Test case not found")
        project_ids = tc_project["projectid"]  # Array of project IDs
        if not project_ids:
            raise HTTPException(status_code=400, detail="No project associated with this test case")

        # 4. Verify user has access to any of the projects
        access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = $1 AND projectid && $2",
            userid, project_ids
        )
        if not access:
            raise HTTPException(status_code=403, detail="You are not authorized for this test case's project")

        # 5. Insert script into testscript table
        # Use the first projectid (assuming one primary project for simplicity)
        project_id = project_ids[0]
        await conn.execute(
            """
            INSERT INTO testscript (testcaseid, projectid, script)
            VALUES ($1, $2, $3)
            ON CONFLICT (testcaseid) DO UPDATE SET
              script = EXCLUDED.script
            """,
            testcaseid, project_id, script_text
        )

        return models.TestScriptResponse(
            testcaseid=testcaseid,
            projectid=project_id,
            message="Script uploaded successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script upload failed: {str(e)}")
    finally:
        if conn:
            await conn.close()

from fastapi import Body  # make sure this import is present at the top

@router.post("/normalize-uploaded", response_model=models.NormalizeResponse,
             summary="Normalize uploaded (staged) test case steps with AI")
async def normalize_uploaded(
        payload: dict = Body(...),
        current_user: dict = Depends(get_current_any_user)
):
    """
    Normalize steps for a staged (Excel-uploaded) test case.
    Payload format from UI:

    {
      "testcaseid": "TC0042",
      "original_steps": [
        {
          "Index": 1,
          "Step": "Given user exists in system",
          "TestDataText": "user@example.com, password123",
          "TestData": {}
        },
        ...
      ]
    }

    The AI must return each step as:
    {
      "Index": <int>,
      "Step": <string>,
      "TestDataText": <string>,
      "TestData": <object>   # inferred key/value pairs
    }
    """
    try:
        testcase_id = payload.get("testcaseid")
        original_steps = payload.get("original_steps", [])

        if not testcase_id:
            raise HTTPException(status_code=400, detail="testcaseid missing")

        if not original_steps:
            raise HTTPException(status_code=400, detail="original_steps missing or empty")

        # Prepare minimal view of steps for the AI
        steps_for_ai = [
            {
                "Index": s.get("Index", i + 1),
                "Step": s.get("Step", ""),
                "TestDataText": s.get("TestDataText", "")
            }
            for i, s in enumerate(original_steps)
        ]

        prompt = f"""
You are a senior QA automation engineer.

You will receive a list of test steps with optional 'TestDataText' strings.
For EACH step:

1. Normalize 'Step' into a clean, atomic BDD-style action (Given / When / Then style).
2. Keep 'TestDataText' as a human-readable string.
3. Infer a structured JSON object 'TestData' from 'TestDataText' where possible.
   - Example:
     TestDataText: "user@example.com, password123"
     TestData: {{ "username": "user@example.com", "password": "password123" }}
   - If there is a URL, use: {{ "url": "https://..." }}
   - If only one value is present and no obvious key, use: {{ "value": "<that value>" }}
4. If no test data is present, use an empty object: {{}}.

RETURN ONLY a JSON ARRAY like this (no extra text):

[
  {{
    "Index": 1,
    "Step": "Given the user opens the login page",
    "TestDataText": "https://example.com/login",
    "TestData": {{
      "url": "https://example.com/login"
    }}
  }},
  ...
]

Here are the original steps (Index, Step, TestDataText):

{json.dumps(steps_for_ai, indent=2)}
"""

        text = call_openai_api(
            prompt=prompt,
            max_tokens=2000,
            system_message="You are a QA automation expert. Return only valid JSON arrays."
        )

        # Extract JSON array from response
        start = text.find("[")
        end = text.rfind("]") + 1
        if start == -1 or end <= start:
            raise HTTPException(status_code=500, detail="AI did not return a JSON array")

        raw_array = json.loads(text[start:end])

        # Coerce AI output into strict schema
        normalized_steps = []
        for i, s in enumerate(raw_array):
            step = s.get("Step", "") or ""
            tdt = s.get("TestDataText", "") or ""
            raw_td = s.get("TestData", {})

            # 🔒 Ensure TestData is ALWAYS a dictionary
            if isinstance(raw_td, dict):
                testdata = raw_td
            elif raw_td is None or raw_td == "":
                testdata = {}
            else:
                # Gemini returned a string or something else → wrap it
                testdata = {"value": str(raw_td)}

            normalized_steps.append({
                "Index": s.get("Index", i + 1),
                "Step": step,
                "TestDataText": tdt,
                "TestData": testdata
            })

        # Also normalize original_steps into full objects for the response
        original_for_response = []
        for idx, s in enumerate(original_steps):
            original_for_response.append({
                "Index": s.get("Index", idx + 1),
                "Step": s.get("Step", "") or "",
                "TestDataText": s.get("TestDataText", "") or "",
                "TestData": s.get("TestData", {}) or {}
            })

        return models.NormalizeResponse(
            testcaseid=testcase_id,
            original_steps=original_for_response,
            normalized_steps=normalized_steps,
            message="Normalization successful"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Normalization (uploaded) failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Normalization failed: {e}")


@router.get("/testcases/details", response_model=models.TestCaseDetails,
            summary="Get test case details with scenarios and steps (requires login + project access)")
async def get_testcase_details(
        testcaseids: str,
        current_user: dict = Depends(get_current_any_user)
):
    """
    Retrieve detailed test case information including scenarios, prerequisites, and steps.
    Requires user to be logged in and assigned to the project.

    Args:
        testcaseids: Comma-separated test case IDs (e.g., "TC001,TC002")
        current_user: Current authenticated user (injected via dependency)

    Returns:
        TestCaseDetails with list of scenarios containing steps and prerequisites
    """
    if not testcaseids:
        raise HTTPException(status_code=400, detail="testcaseids parameter is required")

    ids = [tcid.strip() for tcid in testcaseids.split(',') if tcid.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No valid testcaseids provided")

    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Get user's projects
        user_proj_row = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1",
            userid
        )
        if not user_proj_row:
            raise HTTPException(status_code=403, detail="Not assigned to any project")
        allowed_projects = set(user_proj_row["projectid"])

        scenarios = []
        for tcid in ids:
            # Fetch testcase
            tc = await conn.fetchrow(
                """
                SELECT testdesc, pretestid, prereq, tag, projectid
                FROM testcase
                WHERE testcaseid = $1
                """,
                tcid
            )
            if not tc:
                continue  # Skip if test case not found

            # Validate required columns in testcase
            if not tc['testdesc'] or not tc['projectid']:
                raise HTTPException(status_code=400, detail="Data not found in specified format")

            # Access check - verify user has access to this test case's project
            tc_projects = set(tc['projectid'])
            if not (tc_projects & allowed_projects):
                raise HTTPException(status_code=403, detail=f"No access to testcase {tcid}")

            # Prerequisites
            prerequisites = []
            if tc['pretestid']:
                pretest = await conn.fetchrow(
                    "SELECT testdesc FROM testcase WHERE testcaseid = $1",
                    tc['pretestid']
                )
                if pretest and pretest['testdesc']:
                    prerequisites.append({
                        "PrerequisiteID": tc['pretestid'],
                        "Description": pretest['testdesc']
                    })

            # Fetch steps
            steps_row = await conn.fetchrow(
                "SELECT steps, args FROM teststep WHERE testcaseid = $1",
                tcid
            )
            if not steps_row or not steps_row['steps'] or not steps_row['args']:
                raise HTTPException(status_code=400, detail="Data not found in specified format")

            steps_list = steps_row['steps']
            args_list = steps_row['args']

            # Build steps
            steps = []
            for idx, (step_text, arg) in enumerate(zip(steps_list, args_list), 1):
                key = _extract_field(step_text)
                test_data_text = f"{key}:{arg}" if key and arg else (arg if arg else "")
                test_data = {key: arg} if key and arg else {}
                steps.append({
                    "Index": idx,
                    "Step": step_text,
                    "TestDataText": test_data_text,
                    "TestData": test_data
                })

            # Scenario
            scenario = {
                "ScenarioId": tcid,
                "Description": tc['testdesc'],
                "Prerequisites": prerequisites,
                "IsBdd": True,
                "Status": "draft",
                "Steps": steps
            }
            scenarios.append(scenario)

        if not scenarios:
            raise HTTPException(status_code=404, detail="No valid scenarios found for provided testcaseids")

        return models.TestCaseDetails(Scenarios=scenarios)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch details: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch details: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.post("/normalize-testcase/{testcase_id}", response_model=models.NormalizeResponse,
             summary="Normalize a test case's steps using AI (requires login + project access)")
async def normalize_testcase(
        testcase_id: str,
        current_user: dict = Depends(get_current_any_user)
):
    """
    Normalize a single test case's steps using Azure OpenAI.
    Requires user to be logged in and assigned to the project.
    """
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Get test case and verify access
        tc = await conn.fetchrow(
            "SELECT projectid, testdesc FROM testcase WHERE testcaseid = $1",
            testcase_id
        )
        if not tc:
            raise HTTPException(status_code=404, detail="Test case not found")

        # Check project access
        user_proj_row = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1",
            userid
        )
        if not user_proj_row or not (set(tc['projectid']) & set(user_proj_row['projectid'])):
            raise HTTPException(status_code=403, detail="No access to this test case")

        steps_rows = await conn.fetch(
            """
            SELECT stepnum, steps, args FROM teststep WHERE testcaseid = $1 ORDER BY stepnum
            """,
            testcase_id
        )

        normalized_steps = [
            {
                "Step": row["steps"],
                "Argument": row["args"]
            }
            for row in steps_rows
        ]

        # Normalize using Azure OpenAI
        prompt = f"""You are a QA automation expert. Normalize these test steps into atomic BDD-style steps.
Each step should perform exactly one action.
Return ONLY valid JSON array with: Index, Step, TestDataText, TestData.

Steps: {json.dumps(normalized_steps, indent=2)}"""

        text = call_openai_api(
            prompt=prompt,
            max_tokens=2000,
            system_message="You are a QA automation expert. Return only valid JSON arrays."
        )

        # Extract JSON array from response
        start = text.find("[")
        end = text.rfind("]") + 1
        normalized_steps = json.loads(text[start:end])

        return models.NormalizeResponse(
            testcaseid=testcase_id,
            original_steps=normalized_steps,
            normalized_steps=normalized_steps,
            message="Normalization successful"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Normalization failed: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Normalization failed: {str(e)}")
    finally:
        if conn:
            await conn.close()

@router.post("/replace-normalized/{testcase_id}", response_model=models.TestCaseResponse)
async def replace_normalized(
    testcase_id: str,
    normalized_steps: models.NormalizedStepsUpdate,
    current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Validate testcase exists + access check
        tc = await conn.fetchrow(
            "SELECT projectid, testdesc, pretestid, prereq, tag FROM testcase WHERE testcaseid = $1",
            testcase_id
        )
        if not tc:
            raise HTTPException(status_code=404, detail="Test case not found")

        user_proj_row = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1",
            userid
        )
        if not user_proj_row or not (set(tc['projectid']) & set(user_proj_row['projectid'])):
            raise HTTPException(status_code=403, detail="No access to this test case")

        if not normalized_steps.normalized_steps:
            raise HTTPException(status_code=400, detail="No normalized steps provided")

        print(f"[v0] Updating testcase {testcase_id}: {len(normalized_steps.normalized_steps)} steps")

        # Extract new steps & args from payload
        step_texts = [s.Step for s in normalized_steps.normalized_steps]
        step_args = [s.TestDataText or "" for s in normalized_steps.normalized_steps]

        # Replace steps
        await conn.execute("DELETE FROM teststep WHERE testcaseid = $1", testcase_id)

        await conn.execute(
            """
            INSERT INTO teststep (testcaseid, steps, args, stepnum)
            VALUES ($1, $2, $3, $4)
            """,
            testcase_id,
            step_texts,
            step_args,
            len(step_texts)
        )

        return models.TestCaseResponse(
            testcaseid=testcase_id,
            testdesc=tc['testdesc'],
            pretestid=tc['pretestid'],
            prereq=tc['prereq'],
            tag=tc['tag'],
            projectid=tc['projectid']
        )

    except Exception as e:
        print(f"[v0] Replace failed: {e}")
        raise HTTPException(status_code=500, detail=f"Replace failed: {e}")
    finally:
        if conn:
            await conn.close()


@router.post("/commit-staged-upload", response_model=models.CommitUploadResponse,
             summary="Commit staged test cases to database")
async def commit_staged_upload(
        request: models.CommitUploadData,
        current_user: dict = Depends(get_current_any_user)
):
    """Commit staged test cases to the database with project validation."""
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Get user's projects
        user_proj_row = await conn.fetchrow(
            'SELECT projectid FROM projectuser WHERE userid = $1',
            userid
        )
        if not user_proj_row:
            raise HTTPException(status_code=403, detail="User not assigned to any project")

        allowed_projects_raw = user_proj_row["projectid"]
        if isinstance(allowed_projects_raw, str):
            allowed_projects = {allowed_projects_raw}
        elif isinstance(allowed_projects_raw, list):
            allowed_projects = set(allowed_projects_raw)
        else:
            allowed_projects = set()

        selected_project_id = request.projectid
        if selected_project_id not in allowed_projects:
            raise HTTPException(
                status_code=403,
                detail=f"You do not have access to project {selected_project_id}"
            )

        commit_count = 0

        for tc in request.testcases:
            tc_id = tc.get("testcaseid")
            if not tc_id:
                continue

            try:
                tags = tc.get("tags", [])
                if isinstance(tags, str):
                    tags = [tags]

                # Insert testcase record
                await conn.execute(
                    """
                    INSERT INTO testcase
                      (testcaseid, testdesc, pretestid, prereq, tag, projectid)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    tc_id,
                    tc.get("testdesc", ""),
                    tc.get("pretestid") or None,
                    tc.get("prereq") or None,
                    tags,
                    [selected_project_id]
                )

                # Collect steps and args arrays
                steps = tc.get("steps", [])
                step_texts = [s.get("step", "") for s in steps]
                step_args = [s.get("steparg", "") for s in steps]

                # Insert single row in teststep (array format)
                await conn.execute(
                    """
                    INSERT INTO teststep (testcaseid, steps, args, stepnum)
                    VALUES ($1, $2, $3, $4)
                    """,
                    tc_id,
                    step_texts,
                    step_args,
                    len(step_texts)
                )

                commit_count += 1

            except Exception as e:
                logger.error(f"Failed to commit testcase {tc_id}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to commit testcase {tc_id}: {str(e)}")

        return {"message": f"Upload committed successfully ({commit_count} test cases)",
                "testcases_committed": commit_count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Commit failed: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Commit failed: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.post("/stage-excel-upload", response_model=models.StageUploadResponse,
             summary="Stage parsed Excel data for preview before committing to database")
async def stage_excel_upload(
        upload_data: models.ExcelUploadData,
        current_user: dict = Depends(get_current_any_user)
):
    """
    Validate and stage Excel data. Returns preview-ready test cases.
    Requires user to be logged in and assigned to the project.
    """
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Get user's projects
        user_proj = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1",
            userid
        )
        if not user_proj:
            raise HTTPException(status_code=403, detail="Not assigned to any project")

        user_projectids = user_proj["projectid"]
        if isinstance(user_projectids, str):
            allowed_projects = {user_projectids}
        else:
            allowed_projects = set(user_projectids) if user_projectids else set()

        if not allowed_projects:
            raise HTTPException(status_code=403, detail="No projects assigned to user")

        # Validate project access for each test case
        staged_testcases = []
        for tc in upload_data.testcases:
            if hasattr(tc, 'project_id') and tc.project_id and tc.project_id.strip():
                proj_ids = [p.strip() for p in tc.project_id.split(',') if p.strip()]
            else:
                # If no project specified, use user's first project
                proj_ids = list(allowed_projects)[:1]

            if not proj_ids or not (set(proj_ids) <= allowed_projects):
                raise HTTPException(
                    status_code=403,
                    detail=f"No access to project: {tc.project_id}. Allowed projects: {', '.join(allowed_projects)}"
                )

            # Parse tags
            tags = [t.strip() for t in tc.tags.split(',') if t.strip()] if tc.tags else []

            # Create step objects
            steps_list = []
            step_items = tc.test_steps.split('\n') if tc.test_steps else []
            arg_items = tc.arguments.split('\n') if tc.arguments else []

            for idx, (step, arg) in enumerate(zip(step_items, arg_items), 1):
                if step.strip():
                    steps_list.append({
                        "Index": idx,
                        "Step": step.strip(),
                        "Argument": arg.strip() if arg else ""
                    })

            staged_testcases.append({
                "testcaseid": tc.testcase_id or f"TC{len(staged_testcases) + 1:04d}",
                "testdesc": tc.test_case_description,
                "pretestid": tc.pre_requisite_test_id or None,
                "prereq": tc.pre_requisite_description or "",
                "tags": tags,
                "projectids": proj_ids,
                "steps": steps_list
            })

        return models.StageUploadResponse(
            message="Data staged successfully",
            testcases_count=len(staged_testcases),
            staged_testcases=staged_testcases
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Staging failed: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Staging failed: {str(e)}")
    finally:
        if conn:
            await conn.close()


def _extract_field(step: str) -> str:
    """
    Extract field name from step text based on common keywords.
    Returns the field name (username, password, email, url) or empty string.
    """
    step_lower = step.lower()
    fields = ['username', 'password', 'email', 'url']
    for field in fields:
        if field in step_lower:
            return field
    return ""
