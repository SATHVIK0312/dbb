import sqlite3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

DB_URL = "genai.db"
router = APIRouter()

class UpdateTestCase(BaseModel):
    old_testcaseid: str
    testcaseid: str
    testdesc: str
    pretestid: str
    prereq: str
    tag: str
    projectid: str


@router.get("/testcases/check-exists")
async def check_exists(testcaseid: str, projectid: str):
    conn = sqlite3.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) 
        FROM testcase 
        WHERE testcaseid=? AND projectid=?
    """, (testcaseid, projectid))

    exists = cur.fetchone()[0] > 0
    conn.close()

    return {"exists": exists}


@router.post("/testcases/update-detail")
async def update_detail(req: UpdateTestCase):
    try:
        conn = sqlite3.connect(DB_URL)
        cur = conn.cursor()

        # If testcaseid changed → update PK
        if req.old_testcaseid != req.testcaseid:
            cur.execute("""
                UPDATE testcase SET testcaseid=? 
                WHERE testcaseid=? AND projectid=?
            """, (req.testcaseid, req.old_testcaseid, req.projectid))

        # Update other fields
        cur.execute("""
            UPDATE testcase
            SET testdesc=?, pretestid=?, prereq=?, tag=?
            WHERE testcaseid=? AND projectid=?
        """, (req.testdesc, req.pretestid, req.prereq, req.tag,
              req.testcaseid, req.projectid))

        conn.commit()
        conn.close()

        return {"success": True, "message": "Test case updated."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
