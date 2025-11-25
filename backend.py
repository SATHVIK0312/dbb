from fastapi import FastAPI, HTTPException, Depends, Body, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
import aiosqlite
import asyncio
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright
import string
from datetime import date
from jose import JWTError, jwt
import pandas as pd
import io
import playwright.sync_api as pw
from starlette.responses import FileResponse, JSONResponse
from fastapi.responses import StreamingResponse
import uuid
from selenium import webdriver
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import logging
import json
from datetime import datetime
from pydantic import BaseModel
from typing import List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from typing import List, Dict
from pydantic import BaseModel
import os
import json
import uuid
import logging
import json
import logging
from datetime import datetime
from jose import jwt, JWTError
from fastapi.security import HTTPBearer
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import File, UploadFile, HTTPException, Depends
import pandas as pd
import io

# ====================== YOUR DATABASE ======================
DB_URL = "genai.db"  # Change this to full path if needed: r"C:\path\to\genai.db"

app = FastAPI(title="User Management API", description="API to manage users and projects with auto-generated IDs based on roles", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8003", "http://127.0.0.1:8003", "http://localhost:8501", "http://127.0.0.1:8501", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "your-super-secret-key-change-in-production"
ALGORITHM = "HS256"
security = HTTPBearer()

app = FastAPI(title="User Management API",
            description="API to manage users and projects with auto-generated IDs based on roles", version="1.0.0")

import playwright.sync_api as pw

# ====================== JSON Helpers for Lists ======================
import json as json_lib
def to_json(val): return json_lib.dumps(val or [])
def from_json(val):
    if not val or val == "[]": return []
    try: return json_lib.loads(val)
    except: return []

# ====================== MODELS (All your original ones) ======================
class ExecutionLog(BaseModel):
    timestamp: str = datetime.now().isoformat()
    message: str
    status: str

class ExecutionResponse(BaseModel):
    testcaseid: str
    script_type: str
    status: str
    logs: List[ExecutionLog] = []

class TestScriptResponse(BaseModel):
    testcaseid: str
    projectid: str
    message: str

class ProjectInfo(BaseModel):
    projectid: str
    title: str
    startdate: date
    projecttype: str
    description: Optional[str]

class TestCaseInfo(BaseModel):
    testcaseid: str
    testdesc: str
    pretestid: Optional[str]
    prereq: Optional[str]
    tag: List[str]
    projectid: List[str]

class TestStepInfo(BaseModel):
    testcaseid: str
    steps: List[str]
    args: List[str]
    stepnum: int

class StepResponse(BaseModel):
    steps: List[str]
    args: List[str]
    stepnum: int

class TestCaseWithSteps(BaseModel):
    testcaseid: str
    testdesc: str
    pretestid: Optional[str]
    prereq: Optional[str]
    tag: List[str]
    projectid: List[str]
    steps: StepResponse

class ProjectWithTestCases(BaseModel):
    projectid: str
    title: str
    startdate: date
    projecttype: str
    description: str
    testcases: List[TestCaseWithSteps]

class UserDashboardResponse(BaseModel):
    userid: str
    role: str
    projects: List[ProjectWithTestCases]

class UserCreate(BaseModel):
    name: str
    mail: str
    password: str
    role: str

class UserResponse(BaseModel):
    name: str
    mail: str
    userid: str
    role: str

class LoginCreate(BaseModel):
    username: str
    password: str

class ProjectCreate(BaseModel):
    title: str
    startdate: date
    projecttype: str
    description: str

class AssignmentCreate(BaseModel):
    userid: str
    projectids: List[str]

class ProjectResponse(BaseModel):
    projectid: str
    title: str
    startdate: date
    projecttype: str
    description: str

class AssignmentResponse(BaseModel):
    userid: str
    projectids: List[str]

class BulkAssignmentResponse(BaseModel):
    message: str
    assigned: List[AssignmentResponse]

class TestCaseCreate(BaseModel):
    testdesc: str
    pretestid: str
    prereq: str
    tag: List[str]
    projectid: List[str]

class TestCaseResponse(BaseModel):
    testcaseid: str
    testdesc: str
    pretestid: str
    prereq: str
    tag: List[str]
    projectid: List[str]

class LoginResponse(BaseModel):
    userid: str
    role: str
    token: str
    projects: List[ProjectResponse]

# ====================== DB Connection & Table Creation ======================
async def get_db_connection():
    conn = await aiosqlite.connect(DB_URL)
    conn.row_factory = aiosqlite.Row
    return conn

@app.on_event("startup")
async def create_tables():
    conn = await get_db_connection()
    await conn.executescript('''
        CREATE TABLE IF NOT EXISTS "user" (
            userid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            mail TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS project (
            projectid TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            startdate DATE NOT NULL,
            projecttype TEXT NOT NULL,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS projectuser (
            userid TEXT PRIMARY KEY,
            projectid TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS testcase (
            testcaseid TEXT PRIMARY KEY,
            testdesc TEXT,
            pretestid TEXT,
            prereq TEXT,
            tag TEXT DEFAULT '[]',
            projectid TEXT DEFAULT '[]'
        );
    ''')
    await conn.commit()
    await conn.close()

# ====================== Helpers ======================
def get_prefix_from_role(role: str) -> Optional[str]:
    if not role.startswith("role-"):
        return None
    try:
        role_num = int(role.split("-")[1])
        if 1 <= role_num <= 26:
            return string.ascii_lowercase[role_num - 1]
    except:
        pass
    return None

async def get_next_projectid(conn):
    row = await (await conn.execute("SELECT projectid FROM project ORDER BY projectid DESC LIMIT 1")).fetchone()
    if not row:
        return "PJ0001"
    num = int(row["projectid"][2:]) + 1
    return f"PJ{num:04d}"

async def get_next_testcaseid(conn):
    row = await (await conn.execute("SELECT testcaseid FROM testcase ORDER BY testcaseid DESC LIMIT 1")).fetchone()
    if not row:
        return "TC0001"
    num = int(row["testcaseid"][2:]) + 1
    return f"TC{num:04d}"

def to_json(val): 
    import json as json_lib
    return json_lib.dumps(val or [])

def from_json(val):
    import json as json_lib
    if not val or val == "[]": 
        return []
    try: 
        return json_lib.loads(val)
    except: 
        return []

# ====================== JWT ======================
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        userid = payload.get("userid")
        role = payload.get("role")
        if not userid or role != "role-1":
            raise HTTPException(status_code=403, detail="You are not Authorised")
        return {"userid": userid, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

async def get_current_any_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        userid = payload.get("userid")
        role = payload.get("role")
        if not userid:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return {"userid": userid, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
app.router.lifespan_context = lifespan

# ====================== ENDPOINTS ======================

@app.post("/user/", response_model=UserResponse)
async def create_user(user: UserCreate):
    prefix = get_prefix_from_role(user.role)
    if not prefix:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'role-1' to 'role-26'.")
    conn = await get_db_connection()
    try:
        row = await (await conn.execute("SELECT 1 FROM \"user\" WHERE mail = ?", (user.mail,))).fetchone()
        if row:
            raise HTTPException(status_code=400, detail="Email already exists.")
        count_row = await (await conn.execute("SELECT COUNT(*) AS c FROM \"user\" WHERE userid LIKE ? AND role = ?", (f"{prefix}%", user.role))).fetchone()
        next_num = (count_row["c"] if count_row else 0) + 1
        new_userid = f"{prefix}{next_num}"
        await conn.execute('INSERT INTO "user" (name, mail, password, userid, role) VALUES (?, ?, ?, ?, ?)',
                          (user.name, user.mail, user.password, new_userid, user.role))
        await conn.commit()
        return UserResponse(name=user.name, mail=user.mail, userid=new_userid, role=user.role)
    finally:
        await conn.close()

@app.post("/project/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    conn = await get_db_connection()
    try:
        pid = await get_next_projectid(conn)
        await conn.execute('INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES (?, ?, ?, ?, ?)',
                          (pid, project.title, project.startdate, project.projecttype, project.description))
        await conn.commit()
        return ProjectResponse(projectid=pid, **project.dict())
    finally:
        await conn.close()

@app.post("/login/", response_model=LoginResponse)
async def login_user(login: LoginCreate):
    conn = await get_db_connection()
    try:
        row = await (await conn.execute('SELECT userid, role FROM "user" WHERE name = ? AND password = ?', (login.username, login.password))).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        userid, role = row["userid"], row["role"]
        token = jwt.encode({"userid": userid, "role": role}, SECRET_KEY, algorithm=ALGORITHM)
        row = await (await conn.execute('SELECT projectid FROM projectuser WHERE userid = ?', (userid,))).fetchone()
        projectids = from_json(row["projectid"] if row else None) if row else []
        projects = []
        for pid in projectids:
            proj = await (await conn.execute('SELECT * FROM project WHERE projectid = ?', (pid,))).fetchone()
            if proj:
                projects.append(ProjectResponse(**proj))
        return LoginResponse(userid=userid, role=role, token=token, projects=projects)
    finally:
        await conn.close()

@app.post("/projectuser/", response_model=BulkAssignmentResponse)
async def assign_project_access(
    current_user: dict = Depends(get_current_user),
    assignment: Optional[AssignmentCreate] = Body(None),
    file: Optional[UploadFile] = File(None)
):
    if not assignment and not file:
        raise HTTPException(status_code=400, detail="Provide JSON or Excel")
    conn = await get_db_connection()
    assigned = []
    try:
        if file:
            if not file.filename.endswith('.xlsx'):
                raise HTTPException(status_code=400, detail="Only .xlsx")
            content = await file.read()
            df = pd.read_excel(io.BytesIO(content))
            if not {'userid', 'projectid'}.issubset(df.columns):
                raise HTTPException(status_code=400, detail="Need userid & projectid columns")
            for uid, group in df.groupby('userid'):
                new_pids = [str(x) for x in group['projectid'].dropna().unique()]
                if not new_pids: continue
                row = await (await conn.execute("SELECT projectid FROM projectuser WHERE userid = ?", (uid,))).fetchone()
                existing = from_json(row["projectid"] if row else None)
                all_pids = list(set(existing + new_pids))
                if row:
                    await conn.execute("UPDATE projectuser SET projectid = ? WHERE userid = ?", (to_json(all_pids), uid))
                else:
                    await conn.execute("INSERT INTO projectuser (userid, projectid) VALUES (?, ?)", (uid, to_json(all_pids)))
                assigned.append(AssignmentResponse(userid=uid, projectids=new_pids))
        else:
            uid = assignment.userid
            new_pids = assignment.projectids
            row = await (await conn.execute("SELECT projectid FROM projectuser WHERE userid = ?", (uid,))).fetchone()
            existing = from_json(row["projectid"] if row else None)
            all_pids = list(set(existing + new_pids))
            if row:
                await conn.execute("UPDATE projectuser SET projectid = ? WHERE userid = ?", (to_json(all_pids), uid))
            else:
                await conn.execute("INSERT INTO projectuser (userid, projectid) VALUES (?, ?)", (uid, to_json(all_pids)))
            assigned.append(AssignmentResponse(userid=uid, projectids=new_pids))
        await conn.commit()
        return BulkAssignmentResponse(message="Access assigned successfully.", assigned=assigned)
    finally:
        await conn.close()

# ====================== NEW ENDPOINT: /my-projects (FULLY FIXED FOR SQLITE) ======================
@app.get("/my-projects", response_model=List[ProjectInfo],
        summary="Get all projects assigned to the current user")
async def get_my_projects(current_user: dict = Depends(get_current_any_user)):
    conn = None
    try:
        conn = await get_db_connection()
        userid = current_user["userid"]

        # Get user's project IDs (stored as JSON string)
        proj_row = await (await conn.execute("SELECT projectid FROM projectuser WHERE userid = ?", (userid,))).fetchone()
        if not proj_row or not proj_row["projectid"] or proj_row["projectid"] == "[]":
            return []

        user_project_ids = from_json(proj_row["projectid"])

        # Fetch full project details
        projects = []
        for pid in user_project_ids:
            project = await (await conn.execute(
                """
                SELECT projectid, title, startdate, projecttype, description
                FROM project WHERE projectid = ?
                """,
                (pid,)
            )).fetchone()
            if project:
                projects.append(ProjectInfo(
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

#################################################################

@app.post("/upload-testcases")
async def upload_testcases_excel(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_any_user)   # Any logged-in user
):
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are allowed")

    content = await file.read()
    df = pd.read_excel(io.BytesIO(content))

    expected_cols = {
        "Test Case ID", "Test Case Description", "Pre requisite Test ID",
        "Pre requisite Test Description", "Tags", "Test Steps", "Arguments"
    }
    if not expected_cols.issubset(set(df.columns)):
        raise HTTPException(status_code=400,
                            detail=f"Excel must contain columns: {', '.join(expected_cols)}")

    # Get the user's currently assigned projects
    conn = await get_db_connection()
    try:
        user_id = current_user["userid"]
        row = await (await conn.execute("SELECT projectid FROM projectuser WHERE userid = ?", (user_id,))).fetchone()
        user_projects = from_json(row["projectid"]) if row and row["projectid"] else []
        
        if not user_projects:
            raise HTTPException(status_code=400, detail="You are not assigned to any project!")

        # Take the FIRST project as current active project (or you can make logic for last used, etc.)
        current_project_id = user_projects[0]

        created_count = 0
        current_tc = None
        steps_list = []
        args_list = []

        for _, row in df.iterrows():
            tc_id_raw = row["Test Case ID"]
            if pd.isna(tc_id_raw) or str(tc_id_raw).strip() in ["", "nan"]:
                if current_tc:
                    step_desc = str(row["Test Steps"]) if pd.notna(row["Test Steps"]) else ""
                    arg_val = str(row["Arguments"]) if pd.notna(row["Arguments"]) else ""
                    steps_list.append(step_desc)
                    args_list.append(arg_val)
                continue

            # Save previous test case
            if current_tc:
                no_steps = len(steps_list)
                await conn.execute("""
                    INSERT INTO testcase 
                    (testcaseid, testdesc, pretestid, prereq, tag, projectid, no_steps, created_on, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
                    ON CONFLICT(testcaseid) DO UPDATE SET
                        testdesc=excluded.testdesc,
                        pretestid=excluded.pretestid,
                        prereq=excluded.prereq,
                        tag=excluded.tag,
                        projectid=excluded.projectid,
                        no_steps=excluded.no_steps,
                        created_on=datetime('now'),
                        created_by=excluded.created_by
                """, (current_tc["id"], current_tc["desc"], current_tc["pretestid"],
                      current_tc["prereq"], to_json(current_tc["tags"]), to_json([current_project_id]),
                      no_steps, user_id))

                await conn.execute("""
                    INSERT INTO teststep (testcaseid, steps, args, stepnum, created_on)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(testcaseid) DO UPDATE SET
                        steps=excluded.steps, args=excluded.args, stepnum=excluded.stepnum
                """, (current_tc["id"], to_json(steps_list), to_json(args_list), no_steps))

                created_count += 1

            # New test case
            tc_id = str(tc_id_raw).strip()
            tags_raw = str(row["Tags"]) if pd.notna(row["Tags"]) else ""
            tags = [t.strip() for t in tags_raw.split(",") if t.strip() and t.strip() != "nan"]

            current_tc = {
                "id": tc_id,
                "desc": str(row["Test Case Description"]) if pd.notna(row["Test Case Description"]) else "",
                "pretestid": str(row["Pre requisite Test ID"]) if pd.notna(row["Pre requisite Test ID"]) else "",
                "prereq": str(row["Pre requisite Test Description"]) if pd.notna(row["Pre requisite Test Description"]) else "",
                "tags": tags
            }
            steps_list = []
            args_list = []

            if pd.notna(row["Test Steps"]):
                steps_list.append(str(row["Test Steps"]))
                args_list.append(str(row["Arguments"]) if pd.notna(row["Arguments"]) else "")

        # Save the last one
        if current_tc:
            no_steps = len(steps_list)
            await conn.execute("""
                INSERT INTO testcase 
                (testcaseid, testdesc, pretestid, prereq, tag, projectid, no_steps, created_on, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
                ON CONFLICT(testcaseid) DO UPDATE SET
                    testdesc=excluded.testdesc, pretestid=excluded.pretestid,
                    prereq=excluded.prereq, tag=excluded.tag,
                    projectid=excluded.projectid, no_steps=excluded.no_steps,
                    created_on=datetime('now'), created_by=excluded.created_by
            """, (current_tc["id"], current_tc["desc"], current_tc["pretestid"],
                  current_tc["prereq"], to_json(current_tc["tags"]), to_json([current_project_id]),
                  no_steps, user_id))

            await conn.execute("""
                INSERT INTO teststep (testcaseid, steps, args, stepnum, created_on)
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(testcaseid) DO UPDATE SET
                    steps=excluded.steps, args=excluded.args, stepnum=excluded.stepnum
            """, (current_tc["id"], to_json(steps_list), to_json(args_list), no_steps))
            created_count += 1

        await conn.commit()
        return {
            "message": "Test cases uploaded successfully!",
            "project_used": current_project_id,
            "created_count": created_count,
            "created_by": user_id
        }

    except Exception as e:
        await conn.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        await conn.close()

# ====================== NEW ENDPOINT: Get Test Cases for a Project ======================
@app.get("/projects/{projectid}/testcases")
async def get_project_testcases(
    projectid: str,
    current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await get_db_connection()
        userid = current_user["userid"]

        # Step 1: Check if user has access to this project
        row = await (await conn.execute(
            "SELECT projectid FROM projectuser WHERE userid = ?", 
            (userid,)
        )).fetchone()

        if not row or not row["projectid"]:
            raise HTTPException(status_code=403, detail="You are not assigned to any project")

        user_project_ids = from_json(row["projectid"])
        if projectid not in user_project_ids:
            raise HTTPException(status_code=403, detail="You do not have access to this project")

        # Step 2: Fetch all test cases for this project
        # Note: projectid is stored as JSON array string like '["PJ0001"]'
        rows = await (await conn.execute("""
            SELECT 
                testcaseid,
                testdesc,
                pretestid,
                prereq,
                tag,
                created_on,
                created_by
            FROM testcase 
            WHERE projectid LIKE ? 
               OR projectid LIKE ? 
               OR projectid LIKE ? 
               OR projectid = ?
            ORDER BY testcaseid
        """, (
            f'%"projectid": "{projectid}"%',     # if stored as object (future)
            f'[{projectid}]',                    # exact match as array
            f'%"{projectid}"%',                  # inside array
            projectid                            # fallback
        ))).fetchall()

        # Better way: use JSON contains (SQLite 3.38+ supports it)
        # If your SQLite supports JSON1, use this instead (recommended):
        try:
            rows = await (await conn.execute("""
                SELECT 
                    testcaseid, testdesc, pretestid, prereq, tag,
                    created_on, created_by
                FROM testcase 
                WHERE json_contains(projectid, ?) 
                   OR projectid = ?
                ORDER BY testcaseid
            """, (f'"{projectid}"', projectid))).fetchall()
        except:
            # Fallback for older SQLite
            rows = await (await conn.execute("""
                SELECT testcaseid, testdesc, pretestid, prereq, tag, created_on, created_by
                FROM testcase 
                WHERE projectid LIKE ?
                ORDER BY testcaseid
            """, (f'%{projectid}%',))).fetchall()

        # Step 3: Format response
        result = []
        for r in rows:
            tags = from_json(r["tag"]) if r["tag"] else []
            result.append({
                "testcaseid": r["testcaseid"],
                "testdesc": r["testdesc"] or "",
                "pretestid": r["pretestid"] or "",
                "prereq": r["prereq"] or "",
                "tags": tags,
                "created_by": r["created_by"] or "unknown",
                "created_on": r["created_on"] or "",
                "updated_on": r["created_on"] or ""  # placeholder - can add real column later
            })

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching test cases: {str(e)}")
    finally:
        if conn:
            await conn.close()

# ====================== NEW ENDPOINT: Get Steps for a Test Case ======================
@app.get("/testcases/{testcase_id}/steps")
async def get_testcase_steps(
    testcase_id: str,
    current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await get_db_connection()
        userid = current_user["userid"]

        # Step 1: Get the test case and its project(s)
        tc_row = await (await conn.execute(
            "SELECT projectid, testdesc FROM testcase WHERE testcaseid = ?",
            (testcase_id,)
        )).fetchone()

        if not tc_row:
            raise HTTPException(status_code=404, detail="Test case not found")

        # Extract project IDs (stored as JSON array string like '["PJ0001"]' or '["PJ0001","PJ0002"]')
        project_ids = from_json(tc_row["projectid"])
        if not project_ids:
            raise HTTPException(status_code=403, detail="Test case has no associated project")

        # Step 2: Check if user has access to ANY of these projects
        user_row = await (await conn.execute(
            "SELECT projectid FROM projectuser WHERE userid = ?",
            (userid,)
        )).fetchone()

        if not user_row or not user_row["projectid"]:
            raise HTTPException(status_code=403, detail="You are not assigned to any project")

        user_projects = from_json(user_row["projectid"])

        # Check for intersection
        has_access = any(pid in user_projects for pid in project_ids)
        if not has_access:
            raise HTTPException(status_code=403, detail="You do not have access to this test case's project")

        # Step 3: Fetch steps and args
        steps_row = await (await conn.execute(
            "SELECT steps, args, stepnum FROM teststep WHERE testcaseid = ?",
            (testcase_id,)
        )).fetchone()

        if not steps_row:
            raise HTTPException(status_code=404, detail="No steps found for this test case")

        steps_list = from_json(steps_row["steps"])
        args_list = from_json(steps_row["args"])

        return {
            "testcaseid": testcase_id,
            "testdesc": tc_row["testdesc"] or "",
            "steps": steps_list,
            "args": args_list,
            "stepnum": steps_row["stepnum"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching test case steps: {str(e)}")
    finally:
        if conn:
            await conn.close()

# ====================== UPDATE TESTCASE + STEPS ======================
@app.put("/testcases/{testcase_id}")
async def update_testcase(
    testcase_id: str,
    file: UploadFile = File(...),  # Reuse Excel format for simplicity
    current_user: dict = Depends(get_current_any_user)
):
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files allowed")

    conn = None
    try:
        conn = await get_db_connection()
        userid = current_user["userid"]

        # 1. Check if test case exists and user has access
        tc_row = await (await conn.execute(
            "SELECT projectid FROM testcase WHERE testcaseid = ?", (testcase_id,)
        )).fetchone()

        if not tc_row:
            raise HTTPException(status_code=404, detail="Test case not found")

        project_ids = from_json(tc_row["projectid"])
        user_projects_row = await (await conn.execute(
            "SELECT projectid FROM projectuser WHERE userid = ?", (userid,)
        )).fetchone()

        if not user_projects_row:
            raise HTTPException(status_code=403, detail="Access denied")

        user_projects = from_json(user_projects_row["projectid"])
        if not any(p in user_projects for p in project_ids):
            raise HTTPException(status_code=403, detail="You do not have access to update this test case")

        # 2. Read new data from Excel (same format as upload)
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))

        expected = {"Test Case ID", "Test Case Description", "Pre requisite Test ID",
                    "Pre requisite Test Description", "Tags", "Test Steps", "Arguments"}
        if not expected.issubset(set(df.columns)):
            raise HTTPException(status_code=400, detail=f"Missing columns: {expected - set(df.columns)}")

        # 3. Parse only the matching testcase_id
        new_desc = new_pretestid = new_prereq = ""
        new_tags = []
        new_steps = []
        new_args = []

        for _, row in df.iterrows():
            row_id = str(row["Test Case ID"] or "").strip()
            if row_id != testcase_id:
                continue  # skip others

            new_desc = str(row["Test Case Description"] or "") if pd.notna(row["Test Case Description"]) else ""
            new_pretestid = str(row["Pre requisite Test ID"] or "") if pd.notna(row["Pre requisite Test ID"]) else ""
            new_prereq = str(row["Pre requisite Test Description"] or "") if pd.notna(row["Pre requisite Test Description"]) else ""

            tags_raw = str(row["Tags"] or "") if pd.notna(row["Tags"]) else ""
            new_tags = [t.strip() for t in tags_raw.split(",") if t.strip() and t.strip() != "nan"]

            # Collect all steps
            if pd.notna(row["Test Steps"]):
                new_steps.append(str(row["Test Steps"]))
                new_args.append(str(row["Arguments"] or "") if pd.notna(row["Arguments"]) else "")

            # Handle continuation rows
            if pd.isna(row["Test Case ID"]) or row_id in ["", "nan"]:
                if pd.notna(row["Test Steps"]):
                    new_steps.append(str(row["Test Steps"]))
                    new_args.append(str(row["Arguments"] or "") if pd.notna(row["Arguments"]) else "")

        if not new_steps:
            raise HTTPException(status_code=400, detail="No steps found in uploaded file")

        # 4. Update testcase and teststep
        no_steps = len(new_steps)

        await conn.execute("""
            UPDATE testcase SET
                testdesc = ?, pretestid = ?, prereq = ?, tag = ?,
                no_steps = ?, created_on = datetime('now'), created_by = ?
            WHERE testcaseid = ?
        """, (new_desc, new_pretestid, new_prereq, to_json(new_tags), no_steps, userid, testcase_id))

        await conn.execute("""
            INSERT OR REPLACE INTO teststep (testcaseid, steps, args, stepnum)
            VALUES (?, ?, ?, ?)
        """, (testcase_id, to_json(new_steps), to_json(new_args), no_steps))

        await conn.commit()
        return {
            "message": "Test case updated successfully",
            "testcaseid": testcase_id,
            "steps_updated": no_steps
        }

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            await conn.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
    finally:
        if conn:
            await conn.close()


# ====================== DELETE TESTCASE + STEPS ======================
@app.delete("/testcases/{testcase_id}")
async def delete_testcase(
    testcase_id: str,
    current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await get_db_connection()
        userid = current_user["userid"]

        # 1. Check access
        tc_row = await (await conn.execute(
            "SELECT projectid FROM testcase WHERE testcaseid = ?", (testcase_id,)
        )).fetchone()

        if not tc_row:
            raise HTTPException(status_code=404, detail="Test case not found")

        project_ids = from_json(tc_row["projectid"])
        user_row = await (await conn.execute(
            "SELECT projectid FROM projectuser WHERE userid = ?", (userid,)
        )).fetchone()

        if not user_row:
            raise HTTPException(status_code=403, detail="Access denied")

        user_projects = from_json(user_row["projectid"])
        if not any(p in user_projects for p in project_ids):
            raise HTTPException(status_code=403, detail="You cannot delete this test case")

        # 2. Delete from both tables
        await conn.execute("DELETE FROM teststep WHERE testcaseid = ?", (testcase_id,))
        await conn.execute("DELETE FROM testcase WHERE testcaseid = ?", (testcase_id,))

        await conn.commit()
        return {"message": f"Test case {testcase_id} and its steps deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            await conn.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
    finally:
        if conn:
            await conn.close()

# ====================== PAGINATED TEST CASES FOR A PROJECT ======================
@app.get("/projects/{project_id}/testcases/paginated")
async def get_testcases_paginated(
    project_id: str,
    page: int = 1,
    page_size: int = 10,
    current_user: dict = Depends(get_current_any_user)
):
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 10
    if page_size > 100:
        page_size = 100  # limit to prevent abuse

    conn = None
    try:
        conn = await get_db_connection()
        userid = current_user["userid"]

        # Step 1: Verify user has access to this project
        user_row = await (await conn.execute(
            "SELECT projectid FROM projectuser WHERE userid = ?",
            (userid,)
        )).fetchone()

        if not user_row or not user_row["projectid"]:
            raise HTTPException(status_code=403, detail="You are not assigned to any project")

        user_projects = from_json(user_row["projectid"])
        if project_id not in user_projects:
            raise HTTPException(status_code=403, detail="You do not have access to this project")

        # Step 2: Count total test cases in this project
        count_rows = await (await conn.execute("""
            SELECT COUNT(*) as total 
            FROM testcase 
            WHERE projectid LIKE ?
        """, (f'%{project_id}%',))).fetchone()

        total_count = count_rows["total"] if count_rows else 0
        total_pages = (total_count + page_size - 1) // page_size
        if page > total_pages and total_pages > 0:
            page = total_pages

        offset = (page - 1) * page_size

        # Step 3: Fetch paginated test cases
        rows = await (await conn.execute("""
            SELECT 
                testcaseid, testdesc, pretestid, prereq, tag,
                created_on, created_by, no_steps
            FROM testcase 
            WHERE projectid LIKE ?
            ORDER BY testcaseid
            LIMIT ? OFFSET ?
        """, (f'%{project_id}%', page_size, offset))).fetchall()

        # Step 4: Build response with steps count (from no_steps column)
        testcases = []
        for r in rows:
            tags = from_json(r["tag"]) if r["tag"] else []
            testcases.append({
                "testcaseid": r["testcaseid"],
                "testdesc": r["testdesc"] or "",
                "pretestid": r["pretestid"] or "",
                "prereq": r["prereq"] or "",
                "tag": tags,
                "created_by": r["created_by"] or "unknown",
                "created_on": r["created_on"] or "",
                "steps_count": r["no_steps"] or 0
            })

        return {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "testcases": testcases,
            "message": "Test cases retrieved successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching test cases: {str(e)}")
    finally:
        if conn:
            await conn.close()


import google.generativeai as genai
import traceback

# Configure once at startup (add this near the top, after imports)
genai.configure(api_key="YOUR_GEMINI_API_KEY_HERE")  # Replace with your key or use env var

@app.post("/normalize-uploaded")
async def normalize_uploaded(
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_any_user)
):
    try:
        testcase_id = payload.get("testcaseid")
        original_steps = payload.get("original_steps", [])

        if not testcase_id:
            raise HTTPException(status_code=400, detail="testcaseid is required")
        if not original_steps:
            raise HTTPException(status_code=400, detail="original_steps cannot be empty")

        # Prepare clean input for Gemini
        steps_input = []
        for i, step in enumerate(original_steps):
            idx = step.get("Index", i + 1)
            text = step.get("Step", "").strip()
            data_text = step.get("TestDataText", "").strip()
            steps_input.append({"Index": idx, "Step": text, "TestDataText": data_text})

        prompt = f"""
You are an expert QA automation engineer specializing in clean, atomic, BDD-style test steps.

Given the following raw test steps from an Excel upload, normalize them as follows:

Rules:
1. Rewrite each Step into clear, actionable, BDD-style (Given/When/Then)
2. Keep TestDataText as human-readable string
3. Infer structured TestData JSON object:
   - If email + password → {{"username": "...", "password": "..."}}
   - If URL → {{"url": "https://..."}}
   - If single value → {{"value": "..."}}
   - If empty → {{}}

Return ONLY a valid JSON array. No explanations.

Input:
{json.dumps(steps_input, indent=2)}

Output format:
[
  {{
    "Index": 1,
    "Step": "When the user enters valid credentials and clicks login",
    "TestDataText": "user@example.com, password123",
    "TestData": {{"username": "user@example.com", "password": "password123"}}
  }}
]
"""

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Extract JSON array
        start = raw_text.find("[")
        end = raw_text.rfind("]") + 1
        if start == -1 or end == 0:
            raise HTTPException(status_code=500, detail="AI did not return valid JSON")

        try:
            normalized_raw = json.loads(raw_text[start:end])
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON from AI: {e}")

        # Validate and clean output
        normalized_steps = []
        for i, item in enumerate(normalized_raw):
            step_text = str(item.get("Step", "") or "").strip()
            data_text = str(item.get("TestDataText", "") or "").strip()
            test_data = item.get("TestData", {})

            if not isinstance(test_data, dict):
                test_data = {"value": str(test_data)} if test_data else {}

            normalized_steps.append({
                "Index": item.get("Index", i + 1),
                "Step": step_text,
                "TestDataText": data_text,
                "TestData": test_data
            })

        return {
            "testcaseid": testcase_id,
            "original_steps": original_steps,
            "normalized_steps": normalized_steps,
            "message": "Steps normalized successfully by AI"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Normalization failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="AI normalization failed")


@app.get("/testcases/details")
async def get_testcase_details(
    testcaseids: str,
    current_user: dict = Depends(get_current_any_user)
):
    if not testcaseids:
        raise HTTPException(status_code=400, detail="testcaseids parameter is required")

    ids = [tid.strip() for tid in testcaseids.split(",") if tid.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No valid test case IDs provided")

    conn = None
    try:
        conn = await get_db_connection()
        userid = current_user["userid"]

        # Get user's assigned projects
        user_row = await (await conn.execute(
            "SELECT projectid FROM projectuser WHERE userid = ?", (userid,)
        )).fetchone()

        if not user_row or not user_row["projectid"]:
            raise HTTPException(status_code=403, detail="You are not assigned to any project")

        user_projects = set(from_json(user_row["projectid"]))
        scenarios = []

        for tcid in ids:
            # Fetch test case
            tc = await (await conn.execute(
                "SELECT testdesc, pretestid, prereq, tag, projectid FROM testcase WHERE testcaseid = ?",
                (tcid,)
            )).fetchone()

            if not tc:
                continue  # Skip missing

            tc_projects = set(from_json(tc["projectid"]))
            if not (tc_projects & user_projects):
                raise HTTPException(status_code=403, detail=f"No access to test case {tcid}")

            # Prerequisites
            prerequisites = []
            if tc["pretestid"]:
                pre_row = await (await conn.execute(
                    "SELECT testdesc FROM testcase WHERE testcaseid = ?", (tc["pretestid"],)
                )).fetchone()
                if pre_row:
                    prerequisites.append({
                        "PrerequisiteID": tc["pretestid"],
                        "Description": pre_row["testdesc"] or ""
                    })

            # Fetch steps
            steps_row = await (await conn.execute(
                "SELECT steps, args FROM teststep WHERE testcaseid = ?", (tcid,)
            )).fetchone()

            if not steps_row or not steps_row["steps"]:
                steps_list = []
                args_list = []
            else:
                steps_list = from_json(steps_row["steps"])
                args_list = from_json(steps_row["args"])

            # Build steps with TestData
            steps = []
            for idx, (step_text, arg) in enumerate(zip(steps_list, args_list), 1):
                # Simple extraction: if step contains "username", "password", etc.
                test_data = {}
                test_data_text = arg

                if arg and "," in arg:
                    parts = [p.strip() for p in arg.split(",")]
                    if len(parts) == 2:
                        test_data = {"username": parts[0], "password": parts[1]}
                    elif "http" in arg:
                        test_data = {"url": arg}
                    else:
                        test_data = {"value": arg}
                elif arg:
                    test_data = {"value": arg}

                steps.append({
                    "Index": idx,
                    "Step": step_text,
                    "TestDataText": test_data_text,
                    "TestData": test_data
                })

            scenarios.append({
                "ScenarioId": tcid,
                "Description": tc["testdesc"] or "",
                "Prerequisites": prerequisites,
                "IsBdd": True,
                "Status": "draft",
                "Steps": steps
            })

        if not scenarios:
            raise HTTPException(status_code=404, detail="No accessible test cases found")

        return {"Scenarios": scenarios}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_testcase_details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch test case details")
    finally:
        if conn:
            await conn.close()
            

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="debug")
