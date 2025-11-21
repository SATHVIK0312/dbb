from fastapi import FastAPI, HTTPException, Depends, Body, File, UploadFile, Form
# from fastapi import StreamingResponse # type: ignore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
# import asyncpg                                 # ← REMOVED
import aiosqlite                                  # ← ADDED (only change)
import asyncio
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright
import string
from datetime import date
from jose import JWTError, jwt # Fixed: Import jwt from jose
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
from jose import jwt, JWTError # For token validation
from fastapi.security import HTTPBearer
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="User Management API", description="API to manage users and projects with auto-generated IDs based on roles", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8003", "http://127.0.0.1:8003", "http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================== SQLITE DB URL ======================
DB_URL = "test_management.db"   # ← Your local SQLite file (this is the only real change)

# JWT Configuration
SECRET_KEY = "your-super-secret-key-change-in-production"
ALGORITHM = "HS256"
security = HTTPBearer()

app = FastAPI(title="User Management API",
            description="API to manage users and projects with auto-generated IDs based on roles", version="1.0.0")

import playwright.sync_api as pw

async def log_generator(script_content, script_type):
    if script_type == "playwright":
        with pw.sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            # Execute script_content safely (e.g., with exec() and sandbox)
            browser.close()

# ------------------------------------------------------------------
# Response Model for Test Execution
# ------------------------------------------------------------------
class ExecutionLog(BaseModel):
    timestamp: str
    message: str
    status: str # "INFO", "ERROR", "SUCCESS"

class ExecutionResponse(BaseModel):
    testcaseid: str
    script_type: str
    status: str # "STARTED", "RUNNING", "COMPLETED", "FAILED"

# ------------------------------------------------------------------
# Response Model for Test Script Upload
# ------------------------------------------------------------------
class TestScriptResponse(BaseModel):
    testcaseid: str
    projectid: str
    message: str

# ------------------------------------------------------------------
# Response Models for Project & Test Case Endpoints
# ------------------------------------------------------------------
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

class ExecutionLog(BaseModel):
    timestamp: str = datetime.now().isoformat()
    message: str
    status: str # "INFO", "RUNNING", "SUCCESS", "FAILED", "ERROR"

class ExecutionResponse(BaseModel):
    testcaseid: str
    script_type: str # "playwright" or "selenium"
    status: str # "STARTED", "RUNNING", "COMPLETED", "FAILED"
    logs: List[ExecutionLog] = []

# ------------------------------------------------------------------
# Pydantic Response Models for /me
# ------------------------------------------------------------------
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

# Pydantic model for user input
class UserCreate(BaseModel):
    name: str
    mail: str
    password: str
    role: str # Expected format: "role-1", "role-2", etc.

# Pydantic model for user response
class UserResponse(BaseModel):
    name: str
    mail: str
    userid: str
    role: str

# Pydantic model for login input (using 'username' as 'name' for login)
class LoginCreate(BaseModel):
    username: str # This maps to 'name' in the user table
    password: str

# Pydantic model for project creation input
class ProjectCreate(BaseModel):
    title: str
    startdate: date
    projecttype: str
    description: str

# Pydantic model for single assignment input
class AssignmentCreate(BaseModel):
    userid: str
    projectids: List[str]

# Pydantic model for project details/response
class ProjectResponse(BaseModel):
    projectid: str
    title: str
    startdate: date
    projecttype: str
    description: str

# Pydantic model for assignment response
class AssignmentResponse(BaseModel):
    userid: str
    projectids: List[str]

# Pydantic model for bulk response
class BulkAssignmentResponse(BaseModel):
    message: str
    assigned: List[AssignmentResponse]

# Pydantic model for testcase creation input
class TestCaseCreate(BaseModel):
    testdesc: str
    pretestid: str
    prereq: str
    tag: List[str]
    projectid: List[str]

class TestStepResponse(BaseModel):
    testcaseid: str
    steps: List[str]
    args: List[str]
    stepnum: int

class BulkTestCaseResponse(BaseModel):
    testcaseid: str
    message: str
    steps_saved: int

class BulkUploadResponse(BaseModel):
    message: str
    testcases_created: int
    total_steps: int

# Pydantic model for testcase response
class TestCaseResponse(BaseModel):
    testcaseid: str
    testdesc: str
    pretestid: str
    prereq: str
    tag: List[str]
    projectid: List[str]

# Pydantic model for login response (updated with token)
class LoginResponse(BaseModel):
    userid: str
    role: str
    token: str
    projects: List[ProjectResponse]

# ====================== JSON <-> List helpers (SQLite has no arrays) ======================
import json as json_lib
def _to_json(val): return json_lib.dumps(val or [])
def _from_json(val): 
    if not val or val == "[]": return []
    try: return json_lib.loads(val)
    except: return []

# ====================== SQLite Connection ======================
async def get_db_connection():
    conn = await aiosqlite.connect(DB_URL)
    conn.row_factory = aiosqlite.Row
    return conn

# ====================== Table creation on startup ======================
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
            projectid TEXT NOT NULL DEFAULT '[]'   -- JSON array
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

# Function to generate prefix from role
def get_prefix_from_role(role: str) -> Optional[str]:
    if not role.startswith("role-"):
        return None
    try:
        role_num = int(role.split("-")[1])
        if role_num < 1 or role_num > 26:
            return None
        return string.ascii_lowercase[role_num - 1]
    except (ValueError, IndexError):
        return None

# Function to generate next sequential projectid (PJ0001, PJ0002, etc.)
async def get_next_projectid(conn):
    row = await (await conn.execute("SELECT projectid FROM project ORDER BY projectid DESC LIMIT 1")).fetchone()
    if row is None:
        return "PJ0001"
    try:
        num = int(row["projectid"][2:]) + 1
        return f"PJ{num:04d}"
    except (ValueError, IndexError):
        raise HTTPException(status_code=500, detail="Invalid projectid format in database. Expected 'PJxxxx'.")

# Function to generate next sequential testcaseid (TC0001, TC0002, etc.)
async def get_next_testcaseid(conn):
    row = await (await conn.execute("SELECT testcaseid FROM testcase ORDER BY testcaseid DESC LIMIT 1")).fetchone()
    if row is None:
        return "TC0001"
    try:
        num = int(row["testcaseid"][2:]) + 1
        return f"TC{num:04d}"
    except (ValueError, IndexError):
        raise HTTPException(status_code=500, detail="Invalid testcaseid format in database. Expected 'TCxxxx'.")

# JWT dependencies
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        userid: str = payload.get("userid")
        role: str = payload.get("role")
        if userid is None or role != "role-1":
            raise HTTPException(status_code=403, detail="You are not Authorised")
        return {"userid": userid, "role": role}
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid authentication token")

async def get_current_any_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        userid: str = payload.get("userid")
        role: str = payload.get("role")
        if userid is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return {"userid": userid, "role": role}
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
app.router.lifespan_context = lifespan

@app.post("/user/", response_model=UserResponse, summary="Create a new user")
async def create_user(user: UserCreate):
    prefix = get_prefix_from_role(user.role)
    if prefix is None:
        raise HTTPException(status_code=400,
                            detail="Invalid role. Must be 'role-1', 'role-2', etc. (up to role-26 for a-z).")
    conn = None
    try:
        conn = await get_db_connection()
        existing_user = await (await conn.execute('SELECT userid FROM "user" WHERE mail = ?', (user.mail,))).fetchone()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists.")

        count_result = await conn.fetchval(
            'SELECT COUNT(*) FROM "user" WHERE userid LIKE ? AND role = ?',
            (f"{prefix}%", user.role)
        )
        next_num = int(count_result or 0) + 1
        new_userid = f"{prefix}{next_num}"

        await conn.execute(
            'INSERT INTO "user" (name, mail, password, userid, role) VALUES (?, ?, ?, ?, ?)',
            (user.name, user.mail, user.password, new_userid, user.role)
        )
        await conn.commit()
        return UserResponse(name=user.name, mail=user.mail, userid=new_userid, role=user.role)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            await conn.close()

@app.post("/project/", response_model=ProjectResponse, summary="Create a new project")
async def create_project(project: ProjectCreate):
    conn = None
    try:
        conn = await get_db_connection()
        next_projectid = await get_next_projectid(conn)
        await conn.execute(
            'INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES (?, ?, ?, ?, ?)',
            (next_projectid, project.title, project.startdate, project.projecttype, project.description)
        )
        await conn.commit()
        return ProjectResponse(projectid=next_projectid, title=project.title, startdate=project.startdate,
                              projecttype=project.projecttype, description=project.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            await conn.close()

@app.post("/login/", response_model=LoginResponse, summary="Login and retrieve user projects")
async def login_user(login: LoginCreate):
    conn = None
    try:
        conn = await get_db_connection()
        user_record = await (await conn.execute(
            'SELECT userid, role FROM "user" WHERE name = ? AND password = ?',
            (login.username, login.password)
        )).fetchone()
        if not user_record:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        userid = user_record['userid']
        role = user_record['role']
        token = jwt.encode({"userid": userid, "role": role}, SECRET_KEY, algorithm=ALGORITHM)

        project_row = await (await conn.execute('SELECT projectid FROM projectuser WHERE userid = ?', (userid,))).fetchone()
        projectids = _from_json(project_row["projectid"] if project_row else None)

        projects = []
        for pid in projectids:
            project_record = await (await conn.execute('SELECT projectid, title, startdate, projecttype, description FROM project WHERE projectid = ?', (pid,))).fetchone()
            if project_record:
                projects.append(ProjectResponse(**project_record))

        return LoginResponse(userid=userid, role=role, token=token, projects=projects)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            await conn.close()

@app.post("/projectuser/", response_model=BulkAssignmentResponse,
        summary="Assign project access to users (single or bulk via Excel)")
async def assign_project_access(
        current_user: dict = Depends(get_current_user),
        assignment: Optional[AssignmentCreate] = Body(None),
        file: Optional[UploadFile] = File(None)
):
    if not assignment and not file:
        raise HTTPException(status_code=400, detail="Either provide JSON body or upload an Excel file.")
    conn = None
    try:
        conn = await get_db_connection()
        assigned = []
        if file:
            if not file.filename.endswith('.xlsx'):
                raise HTTPException(status_code=400, detail="Only .xlsx files are supported.")
            content = await file.read()
            df = pd.read_excel(io.BytesIO(content))
            required_cols = ['userid', 'projectid']
            if not all(col in df.columns for col in required_cols):
                raise HTTPException(status_code=400, detail=f"Excel must have columns: {', '.join(required_cols)}")
            grouped = df.groupby('userid')['projectid'].apply(lambda x: list(set(str(i) for i in x.dropna()))).to_dict()
            for target_userid, projectids in grouped.items():
                if not projectids: continue
                row = await (await conn.execute('SELECT projectid FROM projectuser WHERE userid = ?', (target_userid,))).fetchone()
                existing = _from_json(row["projectid"] if row else None)
                all_pids = list(set(existing + projectids))
                json_pids = _to_json(all_pids)
                if row:
                    await conn.execute('UPDATE projectuser SET projectid = ? WHERE userid = ?', (json_pids, target_userid))
                else:
                    await conn.execute('INSERT INTO projectuser (userid, projectid) VALUES (?, ?)', (target_userid, json_pids))
                assigned.append(AssignmentResponse(userid=target_userid, projectids=projectids))
        else:
            target_userid = assignment.userid
            projectids = assignment.projectids
            if not projectids:
                raise HTTPException(status_code=400, detail="projectids list cannot be empty.")
            row = await (await conn.execute('SELECT projectid FROM projectuser WHERE userid = ?', (target_userid,))).fetchone()
            existing = _from_json(row["projectid"] if row else None)
            all_pids = list(set(existing + projectids))
            json_pids = _to_json(all_pids)
            if row:
                await conn.execute('UPDATE projectuser SET projectid = ? WHERE userid = ?', (json_pids, target_userid))
            else:
                await conn.execute('INSERT INTO projectuser (userid, projectid) VALUES (?, ?)', (target_userid, json_pids))
            assigned.append(AssignmentResponse(userid=target_userid, projectids=projectids))

        await conn.commit()
        return BulkAssignmentResponse(message="Access assigned successfully.", assigned=assigned)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            await conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="debug")
