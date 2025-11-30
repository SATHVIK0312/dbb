@router.post("/commit-staged-upload", response_model=models.CommitUploadResponse,
             summary="Commit staged test cases to SQLite DB")
async def commit_staged_upload(
        request: models.CommitUploadData,
        current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # -------------------------------------------------------
        # 1) FETCH USER PROJECTS (SQLite version using fetchall)
        # -------------------------------------------------------
        rows = await conn.fetch_all(
            "SELECT projectid FROM projectuser WHERE userid = ?",
            (userid,)
        )

        if not rows:
            raise HTTPException(status_code=403, detail="User not assigned to any project")

        # Since SQLite stores JSON text, decode it
        allowed_raw = rows[0][0]
        try:
            allowed_projects = set(json.loads(allowed_raw))
        except:
            allowed_projects = {allowed_raw}

        # User selected project
        selected_project = request.projectid

        if selected_project not in allowed_projects:
            raise HTTPException(
                status_code=403,
                detail=f"You do not have access to project {selected_project}"
            )

        commit_count = 0

        # -------------------------------------------------------
        # 2) COMMIT EACH TEST CASE
        # -------------------------------------------------------
        for tc in request.testcases:

            tc_id = tc.testcaseid

            # Check if testcase already exists
            existing = await conn.fetch_all(
                "SELECT testcaseid FROM testcase WHERE testcaseid = ?",
                (tc_id,)
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Testcase {tc_id} already exists"
                )

            # Prepare tags JSON
            tags = tc.tags or []
            tags_json = json.dumps(tags)

            # Insert into testcase table
            await conn.execute(
                """
                INSERT INTO testcase
                (testcaseid, testdesc, pretestid, prereq, tag, projectid)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tc_id,
                    tc.testdesc or "",
                    tc.pretestid or "",
                    tc.prereq or "",
                    tags_json,
                    json.dumps([selected_project])   # Stored as JSON
                )
            )

            # Build steps arrays
            step_texts = []
            step_args = []

            for s in tc.steps:
                step_texts.append(s.step or "")
                step_args.append(s.steparg or "")

            # Insert into teststep table
            await conn.execute(
                """
                INSERT INTO teststep (testcaseid, steps, args, stepnum)
                VALUES (?, ?, ?, ?)
                """,
                (
                    tc_id,
                    json.dumps(step_texts),   # JSON array
                    json.dumps(step_args),    # JSON array
                    len(step_texts)
                )
            )

            commit_count += 1

        await conn.commit()

        return models.CommitUploadResponse(
            message=f"Upload committed successfully ({commit_count} test cases)",
            testcases_committed=commit_count
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Commit failed: {e}")
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

        
