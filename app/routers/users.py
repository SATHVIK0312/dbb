from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

import database as db
import utils
import config
import models



security = HTTPBearer()
router = APIRouter()

# ---------------------------------------------------------------------
# JWT dependency to get current user and check role (only role-1 allowed)
# ---------------------------------------------------------------------
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        userid: str = payload.get("userid")
        role: str = payload.get("role")
        if userid is None or role != "role-1":
            raise HTTPException(status_code=403, detail="You are not Authorised")
        return {"userid": userid, "role": role}
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid authentication token")


# ---------------------------------------------------------------------
# JWT dependency, any role allowed
# ---------------------------------------------------------------------
async def get_current_any_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        userid: str = payload.get("userid")
        role: str = payload.get("role")
        if userid is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return {"userid": userid, "role": role}
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid authentication token")


# ---------------------------------------------------------------------
# Create User
# ---------------------------------------------------------------------
@router.post("/user/", response_model=models.UserResponse, summary="Create a new user")
async def create_user(user: models.UserCreate):
    prefix = utils.get_prefix_from_role(user.role)
    if prefix is None:
        raise HTTPException(status_code=400,
            detail="Invalid role. Must be 'role-1', 'role-2', etc. (up to role-26 for a-z).")

    conn = None
    try:
        conn = await db.get_db_connection()

        # Check if email unique
        existing_user = await conn.fetchrow(
            'SELECT userid FROM "user" WHERE mail = $1', user.mail
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists.")

        # Generate new user ID
        count_result = await conn.fetchval(
            'SELECT COUNT(*) FROM "user" WHERE userid LIKE $1 || \'%\' AND role = $2',
            prefix, user.role
        )
        next_num = int(count_result) + 1
        new_userid = f"{prefix}{next_num}"

        # Extra validation to avoid duplicate
        existing_userid = await conn.fetchrow(
            'SELECT userid FROM "user" WHERE userid = $1', new_userid
        )
        if existing_userid:
            raise HTTPException(status_code=500, detail="Failed to generate unique userid. Try again.")

        # Insert record
        await conn.execute(
            '''
            INSERT INTO "user" (name, mail, password, userid, role)
            VALUES ($1, $2, $3, $4, $5)
            ''',
            user.name, user.mail, user.password, new_userid, user.role
        )

        return models.UserResponse(
            name=user.name,
            mail=user.mail,
            userid=new_userid,
            role=user.role
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        if conn:
            await db.release_db_connection(conn)


# ---------------------------------------------------------------------
# Login User
# ---------------------------------------------------------------------
@router.post("/login/", response_model=models.LoginResponse, summary="Login and retrieve user projects")
async def login_user(login: models.LoginCreate):
    conn = None
    try:
        conn = await db.get_db_connection()

        user_record = await conn.fetchrow(
            'SELECT userid, role FROM "user" WHERE name = $1 AND password = $2',
            login.username, login.password
        )
        if not user_record:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        userid = user_record["userid"]
        role = user_record["role"]

        # Generate JWT token
        token = jwt.encode({"userid": userid, "role": role}, config.SECRET_KEY, algorithm=config.ALGORITHM)

        # Fetch projects
        projectids_record = await conn.fetchrow(
            'SELECT projectid FROM projectuser WHERE userid = $1',
            userid
        )

        projects = []
        if projectids_record and projectids_record["projectid"]:
            for pid in projectids_record["projectid"]:
                pr = await conn.fetchrow(
                    'SELECT projectid, title, startdate, projecttype, description FROM project WHERE projectid = $1',
                    pid
                )
                if pr:
                    projects.append(models.ProjectResponse(**pr))

        return models.LoginResponse(
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
            await db.release_db_connection(conn)


# ---------------------------------------------------------------------
# Dashboard /me
# ---------------------------------------------------------------------
@router.get("/me", response_model=models.UserDashboardResponse, summary="Get current user's projects, test cases, and steps")
async def get_user_dashboard(current_user: dict = Depends(get_current_any_user)):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        proj_row = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1", userid
        )

        if not proj_row or not proj_row["projectid"]:
            return models.UserDashboardResponse(
                userid=userid,
                role=current_user["role"],
                projects=[]
            )

        user_project_ids = proj_row["projectid"]
        projects = []

        for pid in user_project_ids:
            project = await conn.fetchrow(
                """
                SELECT projectid, title, startdate, projecttype, description
                FROM project WHERE projectid = $1
                """,
                pid
            )
            if not project:
                continue

            # Fetch test cases
            testcases_raw = await conn.fetch(
                """
                SELECT testcaseid, testdesc, pretestid, prereq, tag, projectid
                FROM testcase
                WHERE $1 = ANY(projectid)
                """,
                pid
            )

            testcases = []
            for tc in testcases_raw:
                steps_row = await conn.fetchrow(
                    "SELECT steps, args, stepnum FROM teststep WHERE testcaseid = $1",
                    tc["testcaseid"]
                )
                steps_data = models.StepResponse(
                    steps=steps_row["steps"] if steps_row else [],
                    args=steps_row["args"] if steps_row else [],
                    stepnum=steps_row["stepnum"] if steps_row else 0
                )

                testcases.append(models.TestCaseWithSteps(
                    testcaseid=tc["testcaseid"],
                    testdesc=tc["testdesc"],
                    pretestid=tc["pretestid"],
                    prereq=tc["prereq"],
                    tag=tc["tag"],
                    projectid=tc["projectid"],
                    steps=steps_data
                ))

            projects.append(models.ProjectWithTestCases(
                projectid=project["projectid"],
                title=project["title"],
                startdate=project["startdate"],
                projecttype=project["projecttype"],
                description=project["description"],
                testcases=testcases
            ))

        return models.UserDashboardResponse(
            userid=userid,
            role=current_user["role"],
            projects=projects
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

    finally:
        if conn:
            await db.release_db_connection(conn)
