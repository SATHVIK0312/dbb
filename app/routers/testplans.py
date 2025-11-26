from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import json
import logging
from typing import List, Dict

import models
import utils
import database as db
from routers.users import get_current_any_user



# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/testplan/{testcase_id}")
async def get_testplan_json(testcase_id: str, current_user: dict = Depends(get_current_any_user)):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # 1. Verify access
        tc_project = await conn.fetchrow("SELECT projectid FROM testcase WHERE testcaseid = $1", testcase_id)
        if not tc_project:
            raise HTTPException(status_code=404, detail="Test case not found")
        project_ids = tc_project["projectid"]

        access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = $1 AND projectid && $2",
            userid, project_ids
        )
        if not access:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # 2. Prerequisite chain
        prereq_chain = await utils.get_prereq_chain(conn, testcase_id)

        # 3. Build JSON result
        result = {
            "pretestid_steps": {},
            "pretestid_scripts": {},
            "current_testid": testcase_id,
            "current_bdd_steps": {}
        }

        # Prerequisites
        for tc_id in prereq_chain[:-1]:
            steps_row = await conn.fetchrow("SELECT steps, args FROM teststep WHERE testcaseid = $1", tc_id)
            if steps_row and steps_row["steps"]:
                result["pretestid_steps"][tc_id] = dict(zip(steps_row["steps"], steps_row["args"]))

            script_row = await conn.fetchrow("SELECT script FROM testscript WHERE testcaseid = $1", tc_id)
            if script_row and script_row["script"]:
                result["pretestid_scripts"][tc_id] = script_row["script"]

        # Current test
        current_steps = await conn.fetchrow("SELECT steps, args FROM teststep WHERE testcaseid = $1", testcase_id)
        if current_steps and current_steps["steps"]:
            result["current_bdd_steps"] = dict(
                zip(current_steps["steps"], current_steps["args"])
            )

        # RETURN RAW JSON
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")
    finally:
        if conn:
            await conn.close()
