from fastapi import APIRouter, HTTPException, Depends, Body, File, UploadFile
import pandas as pd
import io
from typing import List, Optional

import models
import utils
import database as db
from routers.users import get_current_any_user


from .users import get_current_user, get_current_any_user


router = APIRouter()

@router.post("/project/", response_model=models.ProjectResponse, summary="Create a new project")
async def create_project(project: models.ProjectCreate):
    conn = None
    try:
        conn = await db.get_db_connection()

        # Generate next sequential and unique projectid
        next_projectid = await utils.get_next_projectid(conn)

        # Double-check uniqueness (handles potential race conditions or invalid data)
        existing_project = await conn.fetchrow(
            'SELECT projectid FROM project WHERE projectid = $1', next_projectid
        )
        if existing_project:
            raise HTTPException(status_code=500, detail="Failed to generate unique projectid. Please try again.")

        # Insert the project
        await conn.execute(
            '''
            INSERT INTO project (projectid, title, startdate, projecttype, description)
            VALUES ($1, $2, $3, $4, $5)
            ''',
            next_projectid, project.title, project.startdate, project.projecttype, project.description
        )

        return models.ProjectResponse(
            projectid=next_projectid,
            title=project.title,
            startdate=project.startdate,
            projecttype=project.projecttype,
            description=project.description
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        if conn:
            await conn.close()

@router.post("/projectuser/", response_model=models.BulkAssignmentResponse,
          summary="Assign project access to users (single or bulk via Excel)")
async def assign_project_access(
        current_user: dict = Depends(get_current_user),
        assignment: Optional[models.AssignmentCreate] = Body(None),
        file: Optional[UploadFile] = File(None)
):
    if not assignment and not file:
        raise HTTPException(status_code=400, detail="Either provide JSON body or upload an Excel file.")

    conn = None
    try:
        conn = await db.get_db_connection()
        assigned = []

        if file:
            # Handle Excel upload
            if not file.filename.endswith('.xlsx'):
                raise HTTPException(status_code=400, detail="Only .xlsx files are supported.")

            # Read Excel into DataFrame
            content = await file.read()
            df = pd.read_excel(io.BytesIO(content))

            # Validate columns
            required_cols = ['userid', 'projectid']
            if not all(col in df.columns for col in required_cols):
                raise HTTPException(status_code=400, detail=f"Excel must have columns: {', '.join(required_cols)}")

            # Group by userid and collect unique projectids
            grouped = df.groupby('userid')['projectid'].apply(lambda x: list(set(x.dropna().astype(str)))).to_dict()

            for target_userid, projectids in grouped.items():
                if not projectids:
                    continue

                # Assign (append if exists)
                existing_pids = await conn.fetchval('SELECT projectid FROM projectuser WHERE userid = $1',
                                                    target_userid)
                if existing_pids:
                    all_pids = list(set(existing_pids + projectids))
                    await conn.execute('UPDATE projectuser SET projectid = $1 WHERE userid = $2', all_pids,
                                       target_userid)
                else:
                    await conn.execute('INSERT INTO projectuser (userid, projectid) VALUES ($1, $2)', target_userid,
                                       projectids)

                assigned.append(models.AssignmentResponse(userid=target_userid, projectids=projectids))

        else:
            # Handle single JSON assignment
            target_userid = assignment.userid
            projectids = assignment.projectids

            if not projectids:
                raise HTTPException(status_code=400, detail="projectids list cannot be empty.")

            # Assign (append if exists)
            existing_pids = await conn.fetchval('SELECT projectid FROM projectuser WHERE userid = $1', target_userid)
            if existing_pids:
                all_pids = list(set(existing_pids + projectids))
                await conn.execute('UPDATE projectuser SET projectid = $1 WHERE userid = $2', all_pids, target_userid)
            else:
                await conn.execute('INSERT INTO projectuser (userid, projectid) VALUES ($1, $2)', target_userid,
                                   projectids)

            assigned.append(models.AssignmentResponse(userid=target_userid, projectids=projectids))

        return models.BulkAssignmentResponse(
            message="Access assigned successfully.",
            assigned=assigned
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            await conn.close()

@router.get("/my-projects", response_model=List[models.ProjectInfo],
         summary="Get all projects assigned to the current user")
async def get_my_projects(current_user: dict = Depends(get_current_any_user)):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Get user's project IDs
        proj_row = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1", userid
        )
        if not proj_row or not proj_row["projectid"]:
            return []

        user_project_ids = proj_row["projectid"]

        # Fetch full project details
        projects = []
        for pid in user_project_ids:
            project = await conn.fetchrow(
                """
                SELECT projectid, title, startdate, projecttype, description
                FROM project WHERE projectid = $1
                """,
                pid
            )
            if project:
                projects.append(models.ProjectInfo(
                    projectid=project["projectid"],
                    title=project["title"],
                    startdate=project["startdate"],
                    projecttype=project["projecttype"],
                    description=project["description"]
                ))

        return projects

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")
    finally:
        if conn:
            await conn.close()

@router.get("/projects/{projectid}/summary", response_model=dict,
         summary="Get project summary: users count, testcases count, executions stats")
async def get_project_summary(projectid: str, current_user: dict = Depends(get_current_any_user)):
    """
    Returns summary statistics for a project:
    - Number of users with access to the project
    - Number of test cases in the project
    - Total number of past executions
    - Number of successful and failed executions
    """
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # 1. Verify user has access to this project
        user_projects = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1",
            userid
        )
        if not user_projects or not user_projects["projectid"] or projectid not in user_projects["projectid"]:
            raise HTTPException(status_code=403, detail="You do not have access to this project")

        # 2. Count users with access to this project
        # Check each user's projectid array to see if it contains this projectid
        users_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM projectuser
            WHERE $1 = ANY(projectid)
            """,
            projectid
        )

        # 3. Count test cases for this project
        testcases_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM testcase
            WHERE $1 = ANY(projectid)
            """,
            projectid
        )

        # 4. Get execution statistics
        total_executions = await conn.fetchval(
            """
            SELECT COUNT(*) FROM execution
            WHERE EXISTS (
                SELECT 1 FROM testcase
                WHERE testcase.testcaseid = execution.testcaseid
                AND $1 = ANY(testcase.projectid)
            )
            """,
            projectid
        )

        successful_executions = await conn.fetchval(
            """
            SELECT COUNT(*) FROM execution
            WHERE EXISTS (
                SELECT 1 FROM testcase
                WHERE testcase.testcaseid = execution.testcaseid
                AND $1 = ANY(testcase.projectid)
            )
            AND (LOWER(status) = 'success' OR LOWER(status) = 'passed' OR LOWER(status) = 'ok')
            """,
            projectid
        )

        failed_executions = await conn.fetchval(
            """
            SELECT COUNT(*) FROM execution
            WHERE EXISTS (
                SELECT 1 FROM testcase
                WHERE testcase.testcaseid = execution.testcaseid
                AND $1 = ANY(testcase.projectid)
            )
            AND (LOWER(status) = 'failed' OR LOWER(status) = 'error')
            """,
            projectid
        )

        return {
            "projectid": projectid,
            "users_count": users_count or 0,
            "testcases_count": testcases_count or 0,
            "total_executions": total_executions or 0,
            "successful_executions": successful_executions or 0,
            "failed_executions": failed_executions or 0
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG] Error in get_project_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching project summary: {str(e)}")
    finally:
        if conn:
            await conn.close()

@router.get("/projects/{projectid}/testcases", response_model=List[models.TestCaseResponse],
         summary="Get all test cases for a project")
async def get_project_testcases(projectid: str, current_user: dict = Depends(get_current_any_user)):
    """
    Get all test cases belonging to a specific project.
    User must have access to the project.
    """
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # 1. Verify user has access to this project
        user_projects = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1",
            userid
        )
        if not user_projects or not user_projects["projectid"] or projectid not in user_projects["projectid"]:
            raise HTTPException(status_code=403, detail="You do not have access to this project")

        # 2. Fetch all test cases for this project
        testcases = await conn.fetch(
            """
            SELECT testcaseid, testdesc, pretestid, prereq, tag, projectid
            FROM testcase
            WHERE projectid && $1::varchar[]
            ORDER BY testcaseid
            """,
            [projectid]
        )

        # 3. Convert to response model
        return [
            models.TestCaseResponse(
                testcaseid=tc["testcaseid"],
                testdesc=tc["testdesc"],
                pretestid=tc["pretestid"],
                prereq=tc["prereq"],
                tag=tc["tag"] if isinstance(tc["tag"], list) else [tc["tag"]] if tc["tag"] else [],
                projectid=tc["projectid"] if isinstance(tc["projectid"], list) else [tc["projectid"]]
            )
            for tc in testcases
        ]

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG] Error in get_project_testcases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching test cases: {str(e)}")
    finally:
        if conn:
            await conn.close()
