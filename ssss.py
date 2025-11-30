@router.post("/commit-staged-upload", response_model=models.CommitUploadResponse)
async def commit_staged_upload(
        request: models.CommitUploadData,
        current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # User allowed projects
        user_proj = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1",
            userid
        )
        if not user_proj:
            raise HTTPException(status_code=403, detail="User not assigned to any project")

        allowed = user_proj["projectid"]
        if isinstance(allowed, str):
            allowed = {allowed}
        else:
            allowed = set(allowed)

        selected_project = request.projectid
        if selected_project not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"You do not have access to project {selected_project}"
            )

        commit_count = 0

        for tc in request.testcases:
            tc_id = tc.get("testcaseid") or None
            if not tc_id:
                continue

            # Check duplicate
            existing = await conn.fetchrow(
                "SELECT testcaseid FROM testcase WHERE testcaseid = $1 AND $2 = ANY(projectid)",
                tc_id, selected_project
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Test case ID {tc_id} already exists in project {selected_project}"
                )

            tags = tc.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]

            # Insert testcase
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
                [selected_project]
            )

            # Insert steps
            # Extract correct step text and args from structured objects
            steps_data = tc.get("steps", [])

            # Build PURIFIED arrays for Postgres
            step_texts = []
            step_args = []

            for s in steps_data:
                step_texts.append(s.get("step", "") or "")
                step_args.append(s.get("steparg", "") or "")

            await conn.execute(
                """
                INSERT INTO teststep (testcaseid, steps, args, stepnum)
                VALUES ($1, $2, $3, $4)
                """,
                tc_id,
                step_texts,  # VARCHAR[]
                step_args,  # VARCHAR[]
                len(step_texts)  # INTEGER
            )

            commit_count += 1

        return {
            "message": f"Upload committed successfully ({commit_count} test cases)",
            "testcases_committed": commit_count
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Commit failed: {str(e)}")
    finally:
        if conn:
            await conn.close()






from typing import List, Optional, Dict, Any
from pydantic import BaseModel


# ------------------------------------------------------
# Normalized Step (No changes as requested)
# ------------------------------------------------------
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


# ------------------------------------------------------
# MODELS FOR /commit-staged-upload  (SQLite Compatible)
# ------------------------------------------------------

class CommitStep(BaseModel):
    """
    One step inside the commit-staged-upload structure.
    Sent from frontend after normalization.
    """
    step: str
    steparg: Optional[str] = ""
    stepno: Optional[int] = None


class CommitTestCase(BaseModel):
    """
    A single staged test case to commit.
    """
    testcaseid: str
    testdesc: Optional[str] = ""
    pretestid: Optional[str] = ""
    prereq: Optional[str] = ""
    tags: Optional[List[str]] = []
    steps: List[CommitStep]


class CommitUploadData(BaseModel):
    """
    Request body for /commit-staged-upload.
    User selects a single project and sends staged testcases.
    """
    projectid: str
    testcases: List[CommitTestCase]


class CommitUploadResponse(BaseModel):
    """
    Response for /commit-staged-upload.
    """
    message: str
    testcases_committed: int





-----------------------------------------
@router.post("/commit-staged-upload", response_model=models.CommitUploadResponse,
             summary="Commit staged test cases to database (SQLite version)")
async def commit_staged_upload(
        request: models.CommitUploadData,
        current_user: dict = Depends(get_current_any_user)
):
    """Commit staged test cases into SQLite."""
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Validate user project access
        user_proj_row = await conn.execute_fetchone(
            "SELECT projectid FROM projectuser WHERE userid = ?", (userid,)
        )
        if not user_proj_row:
            raise HTTPException(status_code=403, detail="User not assigned to any project")

        allowed_projects_raw = user_proj_row[0]

        if isinstance(allowed_projects_raw, str):
            allowed_projects = {allowed_projects_raw}
        else:
            allowed_projects = set(allowed_projects_raw)

        selected_project = request.projectid
        if selected_project not in allowed_projects:
            raise HTTPException(
                status_code=403,
                detail=f"You do not have access to project {selected_project}"
            )

        commit_count = 0

        for tc in request.testcases:
            tc_id = tc.get("testcaseid")

            if not tc_id:
                continue

            # Check duplicate test case
            existing = await conn.execute_fetchone(
                "SELECT testcaseid FROM testcase WHERE testcaseid = ?",
                (tc_id,)
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Test case {tc_id} already exists"
                )

            # Normalize tags
            tags = tc.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]

            # Store testcase
            await conn.execute(
                """
                INSERT INTO testcase 
                (testcaseid, testdesc, pretestid, prereq, tag, projectid)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tc_id,
                    tc.get("testdesc", ""),
                    tc.get("pretestid") or None,
                    tc.get("prereq") or "",
                    json.dumps(tags),                       # stored as JSON
                    json.dumps([selected_project])          # project array stored as JSON
                )
            )

            # Extract steps from payload
            steps_data = tc.get("steps", [])

            step_texts = []
            step_args = []

            for s in steps_data:
                step_texts.append(s.get("step", "") or "")
                step_args.append(s.get("steparg", "") or "")

            # Insert into teststep table
            await conn.execute(
                """
                INSERT INTO teststep (testcaseid, steps, args, stepnum)
                VALUES (?, ?, ?, ?)
                """,
                (
                    tc_id,
                    json.dumps(step_texts),       # SQLite stores arrays as JSON
                    json.dumps(step_args),
                    len(step_texts)
                )
            )

            commit_count += 1

        await conn.commit()

        return {
            "message": f"Upload committed successfully ({commit_count} test cases)",
            "testcases_committed": commit_count
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Commit failed: {str(e)}")
    finally:
        if conn:
            await conn.close()

        
