@app.get("/documents/{document_id}/test-cases")
async def get_test_cases(document_id: int):
    conn = await get_db_connection()

    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT test_case_id, description, pre_req_id, pre_req_desc,
                       tags, steps, arguments
                FROM test_cases
                WHERE document_id = ?
                ORDER BY id
                """,
                (document_id,)
            )

            rows = await cur.fetchall()

            test_cases = []
            for row in rows:
                test_cases.append({
                    "test_case_id": row["test_case_id"],
                    "description": row["description"],
                    "pre_req_id": row["pre_req_id"],
                    "pre_req_desc": row["pre_req_desc"],
                    "tags": row["tags"].split(",") if row["tags"] else [],
                    "steps": row["steps"].split("\n") if row["steps"] else [],
                    "arguments": row["arguments"].split(",") if row["arguments"] else []
                })

            return {
                "document_id": document_id,
                "total_test_cases": len(test_cases),
                "test_cases": test_cases
            }

    finally:
        await conn.close()




========================================================================

@app.get("/documents/{document_id}/user-stories")
async def get_user_stories(document_id: int):
    conn = await get_db_connection()

    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT story
                FROM user_stories
                WHERE document_id = ?
                ORDER BY id
                """,
                (document_id,)
            )

            rows = await cur.fetchall()

            return {
                "document_id": document_id,
                "total_user_stories": len(rows),
                "user_stories": [row["story"] for row in rows]
            }

    finally:
        await conn.close()



==================================================

@app.get("/documents/{document_id}/software-flow")
async def get_software_flow(document_id: int):
    conn = await get_db_connection()

    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT step
                FROM software_flows
                WHERE document_id = ?
                ORDER BY id
                """,
                (document_id,)
            )

            rows = await cur.fetchall()

            flow = [
                {"step_no": idx + 1, "step": row["step"]}
                for idx, row in enumerate(rows)
            ]

            return {
                "document_id": document_id,
                "total_steps": len(flow),
                "software_flow": flow
            }

    finally:
        await conn.close()
