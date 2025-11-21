from fastapi import FastAPI, HTTPException, Depends, Body, File, UploadFile, Form
# from fastapi import StreamingResponse  # type: ignore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
import asyncpg
import asyncio
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright
import string
from datetime import date
from jose import JWTError, jwt  # Fixed: Import jwt from jose
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
from jose import jwt, JWTError  # For token validation
from fastapi.security import HTTPBearer
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="User Management API", description="API to manage users and projects with auto-generated IDs based on roles", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8003", "http://127.0.0.1:8003", "http://localhost:8501", "http://127.0.0.1:8501"],  # Allow your frontend origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Rest of your code...

# Database connection details
DB_URL = "postgresql://neondb_owner:npg_MQHJ6cGn9gOh@ep-broad-resonance-a1thxhee.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# JWT Configuration
SECRET_KEY = "your-super-secret-key-change-in-production"  # Change this in production
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
    status: str  # "INFO", "ERROR", "SUCCESS"

class ExecutionResponse(BaseModel):
    testcaseid: str
    script_type: str
    status: str  # "STARTED", "RUNNING", "COMPLETED", "FAILED"
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
    status: str  # "INFO", "RUNNING", "SUCCESS", "FAILED", "ERROR"

class ExecutionResponse(BaseModel):
    testcaseid: str
    script_type: str  # "playwright" or "selenium"
    status: str  # "STARTED", "RUNNING", "COMPLETED", "FAILED"
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
    role: str  # Expected format: "role-1", "role-2", etc.


# Pydantic model for user response
class UserResponse(BaseModel):
    name: str
    mail: str
    userid: str
    role: str


# Pydantic model for login input (using 'username' as 'name' for login)
class LoginCreate(BaseModel):
    username: str  # This maps to 'name' in the user table
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


# Dependency to get database connection
async def get_db_connection():
    return await asyncpg.connect(DB_URL)



# def log_generator():
#     yield {"timestamp": datetime.now().isoformat(), "message": "Execution started", "status": "INFO"}
#     if script_type == "playwright":
#         with pw.sync_playwright() as p:
#             browser = p.chromium.launch()
#             page = browser.new_page()
#             yield {"timestamp": datetime.now().isoformat(), "message": "Browser launched", "status": "RUNNING"}
#             # Execute script_content here (e.g., exec(script_content) with safety checks)
#             browser.close()
#     elif script_type == "selenium":
#         driver = webdriver.Chrome()
#         yield {"timestamp": datetime.now().isoformat(), "message": "Browser launched", "status": "RUNNING"}
#         # Execute script_content
#         driver.quit()
#     yield {"timestamp": datetime.now().isoformat(), "message": "Execution completed", "status": "SUCCESS"}

# Function to generate prefix from role
def get_prefix_from_role(role: str) -> Optional[str]:
    if not role.startswith("role-"):
        return None
    try:
        role_num = int(role.split("-")[1])
        if role_num < 1 or role_num > 26:  # Limit to a-z
            return None
        return string.ascii_lowercase[role_num - 1]
    except (ValueError, IndexError):
        return None


# Function to generate next sequential projectid (PJ0001, PJ0002, etc.)
async def get_next_projectid(conn):
    max_pid = await conn.fetchval('SELECT MAX(projectid) FROM project')
    if max_pid is None:
        return "PJ0001"
    try:
        # Extract the numeric part after 'PJ' and increment
        num = int(max_pid[2:]) + 1  # Assumes format 'PJxxxx' where xxxx is 4-digit number
        return f"PJ{num:04d}"  # Pad to 4 digits for consistency
    except (ValueError, IndexError):
        raise HTTPException(status_code=500, detail="Invalid projectid format in database. Expected 'PJxxxx'.")


# Function to generate next sequential testcaseid (TC0001, TC0002, etc.)
async def get_next_testcaseid(conn):
    max_tid = await conn.fetchval('SELECT MAX(testcaseid) FROM testcase')
    if max_tid is None:
        return "TC0001"
    try:
        # Extract the numeric part after 'TC' and increment
        num = int(max_tid[2:]) + 1  # Assumes format 'TCxxxx' where xxxx is 4-digit number
        return f"TC{num:04d}"  # Pad to 4 digits for consistency
    except (ValueError, IndexError):
        raise HTTPException(status_code=500, detail="Invalid testcaseid format in database. Expected 'TCxxxx'.")


# JWT dependency to get current user and check role (for role-1 only)
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


# JWT dependency to get current user for any role
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


# Startup and shutdown events for connection pool (optional, but good practice)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create connection pool if needed
    yield
    # Shutdown: Close pool


app.router.lifespan_context = lifespan


@app.post("/user/", response_model=UserResponse, summary="Create a new user")
async def create_user(user: UserCreate):
    # Validate role
    prefix = get_prefix_from_role(user.role)
    if prefix is None:
        raise HTTPException(status_code=400,
                            detail="Invalid role. Must be 'role-1', 'role-2', etc. (up to role-26 for a-z).")

    conn = None
    try:
        conn = await get_db_connection()

        # Check if email already exists (assuming mail should be unique)
        existing_user = await conn.fetchrow(
            'SELECT userid FROM "user" WHERE mail = $1', user.mail
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists.")

        # Find the next userid for this prefix
        count_result = await conn.fetchval(
            'SELECT COUNT(*) FROM "user" WHERE userid LIKE $1 || \'%\' AND role = $2',
            prefix, user.role
        )
        next_num = int(count_result) + 1
        new_userid = f"{prefix}{next_num}"

        # Check if this userid already exists (in case of role changes or edge cases)
        existing_userid = await conn.fetchrow(
            'SELECT userid FROM "user" WHERE userid = $1', new_userid
        )
        if existing_userid:
            raise HTTPException(status_code=500, detail="Failed to generate unique userid. Please try again.")

        # Insert the user
        await conn.execute(
            '''
            INSERT INTO "user" (name, mail, password, userid, role)
            VALUES ($1, $2, $3, $4, $5)
            ''',
            user.name, user.mail, user.password, new_userid, user.role
        )

        return UserResponse(
            name=user.name,
            mail=user.mail,
            userid=new_userid,
            role=user.role
        )

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

        # Generate next sequential and unique projectid
        next_projectid = await get_next_projectid(conn)

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

        return ProjectResponse(
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


@app.post("/login/", response_model=LoginResponse, summary="Login and retrieve user projects")
async def login_user(login: LoginCreate):
    conn = None
    try:
        conn = await get_db_connection()

        # Check credentials by name (username) and password
        user_record = await conn.fetchrow(
            'SELECT userid, role FROM "user" WHERE name = $1 AND password = $2',
            login.username, login.password
        )

        if not user_record:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        userid = user_record['userid']
        role = user_record['role']

        # Generate JWT token
        token = jwt.encode({"userid": userid, "role": role}, SECRET_KEY, algorithm=ALGORITHM)

        # Get projectids array from projectuser table
        projectids_record = await conn.fetchrow(
            'SELECT projectid FROM projectuser WHERE userid = $1',
            userid
        )

        projects = []
        if projectids_record and projectids_record['projectid']:
            projectids = projectids_record['projectid']  # This is a list of strings

            # Fetch details for each projectid from project table
            for pid in projectids:
                project_record = await conn.fetchrow(
                    'SELECT projectid, title, startdate, projecttype, description FROM project WHERE projectid = $1',
                    pid
                )
                if project_record:
                    projects.append(ProjectResponse(
                        projectid=project_record['projectid'],
                        title=project_record['title'],
                        startdate=project_record['startdate'],  # asyncpg parses date
                        projecttype=project_record['projecttype'],
                        description=project_record['description']
                    ))

        return LoginResponse(
            userid=userid,
            role=role,
            token=token,
            projects=projects
        )

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

                assigned.append(AssignmentResponse(userid=target_userid, projectids=projectids))

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

            assigned.append(AssignmentResponse(userid=target_userid, projectids=projectids))

        return BulkAssignmentResponse(
            message="Access assigned successfully.",
            assigned=assigned
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        if conn:
            await conn.close()



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="debug")
