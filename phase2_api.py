@app.get("/knowledge-center/data")
async def load_knowledge_center_data(
    document_id: int = Query(..., description="Analyzed document ID")
):
    conn = await get_db_connection()

    try:
        # ---------------------------
        # USER STORIES
        # ---------------------------
        user_stories = []
        async with conn.execute(
            """
            SELECT story_id, feature, goal, description
            FROM user_stories
            WHERE document_id = ?
            """,
            (document_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                user_stories.append({
                    "story_id": r["story_id"],
                    "feature": r["feature"],
                    "goal": r["goal"],
                    "description": r["description"]
                })

        # ---------------------------
        # SOFTWARE FLOWS
        # ---------------------------
        flows = []
        async with conn.execute(
            """
            SELECT flow_id, title, steps
            FROM software_flows
            WHERE document_id = ?
            """,
            (document_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                flows.append({
                    "flow_id": r["flow_id"],
                    "title": r["title"],
                    "steps": r["steps"].split("\n")
                })

        # ---------------------------
        # TEST CASES + STEPS
        # ---------------------------
        test_cases = []
        async with conn.execute(
            """
            SELECT
                test_case_id,
                test_case_code,
                description,
                pre_req_test_id,
                pre_req_description,
                tags,
                arguments
            FROM test_cases
            WHERE document_id = ?
            ORDER BY test_case_id
            """,
            (document_id,)
        ) as cursor:
            tc_rows = await cursor.fetchall()

            for tc in tc_rows:
                # Fetch steps per test case
                steps = []
                async with conn.execute(
                    """
                    SELECT step_no, step_description
                    FROM test_case_steps
                    WHERE test_case_id = ?
                    ORDER BY step_no
                    """,
                    (tc["test_case_id"],)
                ) as step_cursor:
                    step_rows = await step_cursor.fetchall()
                    for s in step_rows:
                        steps.append({
                            "step_no": s["step_no"],
                            "step_description": s["step_description"]
                        })

                test_cases.append({
                    "test_case_id": tc["test_case_code"],   # GTC00X
                    "description": tc["description"],
                    "pre_requisite_test_id": tc["pre_req_test_id"],
                    "pre_requisite_description": tc["pre_req_description"],
                    "tags": tc["tags"].split(",") if tc["tags"] else [],
                    "arguments": tc["arguments"],
                    "steps": steps
                })

        return {
            "document_id": document_id,
            "user_stories": user_stories,
            "flows": flows,
            "test_cases": test_cases
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await conn.close()
