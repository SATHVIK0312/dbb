@app.get("/testplan/{testcase_id}")
async def get_testplan_json(
    testcase_id: str,
    current_user: dict = Depends(get_current_any_user)
):
    """
    Returns full test plan JSON for execution:
    - All prerequisite test cases (steps + args) in correct order
    - Current test case BDD steps at the end
    - Ready for AI executor and WPF viewer
    """
    conn = None
    try:
        conn = await get_db_connection()
        userid = current_user["userid"]

        # 1. Get test case and its project(s)
        tc_row = await (await conn.execute(
            "SELECT projectid, pretestid FROM testcase WHERE testcaseid = ?",
            (testcase_id,)
        )).fetchone()

        if not tc_row:
            raise HTTPException(status_code=404, detail="Test case not found")

        project_ids = from_json(tc_row["projectid"])

        # 2. Check user access
        user_row = await (await conn.execute(
            "SELECT projectid FROM projectuser WHERE userid = ?",
            (userid,)
        )).fetchone()

        if not user_row:
            raise HTTPException(status_code=403, detail="You are not assigned to any project")

        user_projects = from_json(user_row["projectid"])
        if not any(pid in user_projects for pid in project_ids):
            raise HTTPException(status_code=403, detail="You do not have access to this test case")

        # 3. Build prerequisite chain recursively (oldest → newest, including current)
        async def get_prereq_chain(tc_id: str, visited=None):
            if visited is None:
                visited = set()
            if tc_id in visited:
                return []  # cycle detected
            visited = visited.copy()  # prevent shared state
            visited.add(tc_id)

            row = await (await conn.execute(
                "SELECT pretestid FROM testcase WHERE testcaseid = ?",
                (tc_id,)
            )).fetchone()

            if not row or not row["pretestid"]:
                return [tc_id]

            chain = await get_prereq_chain(row["pretestid"], visited)
            return chain + [tc_id]

        execution_order = await get_prereq_chain(testcase_id)  # e.g., ["PRE1", "PRE2", "MAIN123"]

        # 4. Build final JSON
        result = {
            "pretestid_steps": {},
            "pretestid_scripts": {},  # optional: populate if you have testscript table
            "current_testid": testcase_id,
            "current_bdd_steps": {}
        }

        # Process all test cases in execution order
        for tc_id in execution_order:
            steps_row = await (await conn.execute(
                "SELECT steps, args FROM teststep WHERE testcaseid = ?",
                (tc_id,)
            )).fetchone()

            if steps_row and steps_row["steps"]:
                steps_list = from_json(steps_row["steps"])
                args_list = from_json(steps_row["args"] or [])  # safety
                step_dict = dict(zip(steps_list, args_list))

                if tc_id == testcase_id:
                    result["current_bdd_steps"] = step_dict
                else:
                    result["pretestid_steps"][tc_id] = step_dict

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_testplan_json failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate test plan: {str(e)}")
    finally:
        if conn:
            await conn.close()
