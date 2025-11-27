@app.get("/execution")
async def get_all_execution_logs(
    current_user: dict = Depends(get_current_any_user)
):
    """
    Returns all execution logs for test cases the current user has access to
    """
    conn = None
    try:
        conn = await get_db_connection()
        userid = current_user["userid"]

        # 1. Get user's assigned projects
        user_row = await (await conn.execute(
            "SELECT projectid FROM projectuser WHERE userid = ?",
            (userid,)
        )).fetchone()

        if not user_row or not user_row["projectid"]:
            return []  # No projects → no logs

        user_projects = from_json(user_row["projectid"])

        # 2. Find all test cases in those projects
        # Since projectid is JSON array string, use LIKE
        accessible_testcase_ids = set()

        for pid in user_projects:
            rows = await (await conn.execute(
                "SELECT testcaseid FROM testcase WHERE projectid LIKE ?",
                (f'%{pid}%',)
            )).fetchall()

            for row in rows:
                accessible_testcase_ids.add(row["testcaseid"])

        if not accessible_testcase_ids:
            return []

        # 3. Fetch execution logs for these test cases
        placeholders = ",".join(["?"] * len(accessible_testcase_ids))
        query = f"""
            SELECT exeid, testcaseid, scripttype, datestamp, exetime, message, output, status
            FROM execution
            WHERE testcaseid IN ({placeholders})
            ORDER BY datestamp DESC, exetime DESC
        """

        rows = await (await conn.execute(query, tuple(accessible_testcase_ids))).fetchall()

        logs = []
        for row in rows:
            logs.append({
                "exeid": row["exeid"],
                "testcaseid": row["testcaseid"],
                "scripttype": row["scripttype"],
                "datestamp": row["datestamp"],
                "exetime": str(row["exetime"]),
                "message": row["message"] or "",
                "output": row["output"] or "",
                "status": row["status"] or "UNKNOWN"
            })

        return logs

    except Exception as e:
        print(f"[ERROR] get_all_execution_logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch execution logs: {str(e)}")
    finally:
        if conn:
            await conn.close()
