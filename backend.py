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
    current_user: dict = Depends(get_current_user)   # admin only, or use get_current_any_user if you want
):
    if not file.filename.endswith(('.xlsx', '.xls')):
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

    conn = await get_db_connection()
    try:
        created = 0
        updated = 0

        current_tc = None
        steps_list = []
        args_list = []

        for _, row in df.iterrows():
            tc_id = str(row["Test Case ID"]).strip()
            if pd.isna(row["Test Case ID"]) or tc_id == "" or tc_id == "nan":
                # continuation row – same test case
                if current_tc is None:
                    continue  # safety
                step_desc = str(row["Test Steps"]) if not pd.isna(row["Test Steps"]) else ""
                arg_val  = str(row["Arguments"]) if not pd.isna(row["Arguments"]) else ""
                steps_list.append(step_desc)
                args_list.append(arg_val)
                continue

            # ---- New test case starts here ----
            # First save the previous one (if any)
            if current_tc:
                no_steps = len(steps_list)
                # upsert testcase
                await conn.execute("""
                    INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, no_steps)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(testcaseid) DO UPDATE SET
                        testdesc=excluded.testdesc,
                        pretestid=excluded.pretestid,
                        prereq=excluded.prereq,
                        tag=excluded.tag,
                        no_steps=excluded.no_steps
                """, (current_tc["id"], current_tc["desc"], current_tc["pretestid"],
                      current_tc["prereq"], to_json(current_tc["tags"]), no_steps))

                # upsert teststep
                await conn.execute("""
                    INSERT INTO teststep (testcaseid, steps, args, stepnum)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(testcaseid) DO UPDATE SET
                        steps=excluded.steps,
                        args=excluded.args,
                        stepnum=excluded.stepnum
                """, (current_tc["id"], to_json(steps_list), to_json(args_list), no_steps))

                if current_tc.get("new"):
                    created += 1
                else:
                    updated += 1

            # Start collecting new test case
            tags_raw = row["Tags"]
            tags = [t.strip() for t in str(tags_raw).split(",") if t.strip() and t.strip() != "nan"]

            current_tc = {
                "id": tc_id,
                "desc": str(row["Test Case Description"]) if not pd.isna(row["Test Case Description"]) else "",
                "pretestid": str(row["Pre requisite Test ID"]) if not pd.isna(row["Pre requisite Test ID"]) else "",
                "prereq": str(row["Pre requisite Test Description"]) if not pd.isna(row["Pre requisite Test Description"]) else "",
                "tags": tags,
                "new": True
            }
            steps_list = []
            args_list = []

            # add the first step if it exists on the same row
            step_desc = str(row["Test Steps"]) if not pd.isna(row["Test Steps"]) else ""
            arg_val  = str(row["Arguments"]) if not pd.isna(row["Arguments"]) else ""
            if step_desc:
                steps_list.append(step_desc)
                args_list.append(arg_val)

        # ---- Save the very last test case ----
        if current_tc:
            no_steps = len(steps_list)
            await conn.execute("""
                INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, no_steps)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(testcaseid) DO UPDATE SET
                    testdesc=excluded.testdesc,
                    pretestid=excluded.pretestid,
                    prereq=excluded.prereq,
                    tag=excluded.tag,
                    no_steps=excluded.no_steps
            """, (current_tc["id"], current_tc["desc"], current_tc["pretestid"],
                  current_tc["prereq"], to_json(current_tc["tags"]), no_steps))

            await conn.execute("""
                INSERT INTO teststep (testcaseid, steps, args, stepnum)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(testcaseid) DO UPDATE SET
                    steps=excluded.steps,
                    args=excluded.args,
                    stepnum=excluded.stepnum
            """, (current_tc["id"], to_json(steps_list), to_json(args_list), no_steps))

            if current_tc.get("new"):
                created += 1
            else:
                updated += 1

        await conn.commit()
        return {
            "message": "Test cases uploaded successfully",
            "created": created,
            "updated": updated
        }

    except Exception as e:
        await conn.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        await conn.close()
        

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="debug")
