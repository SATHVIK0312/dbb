@app.get("/projects/{project_id}/executions/history")
async def get_execution_history(
    project_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_any_user)
):
    """
    Get paginated execution history for a project
    Fully compatible with your current SQLite + JSON projectid setup
    """
    conn = None
    try:
        conn = await get_db_connection()
        userid = current_user["userid"]

        # 1. Verify user has access to this project
        user_row = await (await conn.execute(
            "SELECT projectid FROM projectuser WHERE userid = ?",
            (userid,)
        )).fetchone()

        if not user_row or project_id not in from_json(user_row["projectid"]):
            raise HTTPException(status_code=403, detail="You are not assigned to this project")

        # 2. Get all test cases in this project (projectid stored as JSON array string)
        tc_rows = await (await conn.execute(
            "SELECT testcaseid FROM testcase WHERE projectid LIKE ?",
            (f'%{project_id}%',)
        )).fetchall()

        if not tc_rows:
            return {"total": 0, "executions": []}

        testcase_ids = [row["testcaseid"] for row in tc_rows]

        # 3. Get total count
        placeholders = ",".join("?" for _ in testcase_ids)
        count_query = f"SELECT COUNT(*) as total FROM execution WHERE testcaseid IN ({placeholders})"
        count_row = await (await conn.execute(count_query, testcase_ids)).fetchone()
        total = count_row["total"] if count_row else 0

        # 4. Get paginated executions
        if not testcase_ids:
            return {"total": 0, "executions": []}

        limit = max(1, min(limit, 100))  # safety
        offset = max(0, offset)

        exec_query = f"""
            SELECT exeid, testcaseid, scripttype, datestamp, exetime, status, message, output
            FROM execution
            WHERE testcaseid IN ({placeholders})
            ORDER BY datestamp DESC, exetime DESC
            LIMIT ? OFFSET ?
        """
        exec_rows = await (await conn.execute(exec_query, testcase_ids + [limit, offset])).fetchall()

        executions = []
        for row in exec_rows:
            executions.append({
                "exeid": row["exeid"],
                "testcaseid": row["testcaseid"],
                "scripttype": row["scripttype"] or "unknown",
                "datestamp": str(row["datestamp"]) if row["datestamp"] else "",
                "exetime": str(row["exetime"]) if row["exetime"] else "",
                "status": row["status"] or "UNKNOWN",
                "message": row["message"] or "",
                "output": row["output"] or ""
            })

        return {
            "total": total,
            "executions": executions
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_execution_history: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching execution history: {str(e)}")
    finally:
        if conn:
            await conn.close()
