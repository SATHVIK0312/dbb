from fastapi import FastAPI
import aiosqlite

app = FastAPI()

DB_URL = "your_sqlite_db_path.db"


# ✅ Your existing async DB connector
async def get_db_connection():
    conn = await aiosqlite.connect(DB_URL)
    conn.row_factory = aiosqlite.Row
    return conn


# ============================================================
# 🔥 LOAD ALL KNOWLEDGE CENTER DATA (NO INPUT)
# ============================================================
@app.get("/knowledge-center/all-data")
async def load_all_knowledge_center_data():
    conn = await get_db_connection()

    try:
        # ---------------- USER STORIES ----------------
        async with conn.execute(
            """
            SELECT id, document_id, story
            FROM user_stories
            ORDER BY document_id, id
            """
        ) as cur:
            user_stories = [dict(row) async for row in cur]

        # ---------------- SOFTWARE FLOWS ----------------
        async with conn.execute(
            """
            SELECT id, document_id, step
            FROM software_flow
            ORDER BY document_id, id
            """
        ) as cur:
            software_flows = [dict(row) async for row in cur]

        # ---------------- TEST CASES ----------------
        async with conn.execute(
            """
            SELECT
                id,
                document_id,
                test_case_id,
                description,
                pre_req_id,
                pre_req_desc,
                tags,
                steps,
                arguments
            FROM test_cases
            ORDER BY document_id, id
            """
        ) as cur:
            test_cases = [dict(row) async for row in cur]

        return {
            "status": "success",
            "counts": {
                "user_stories": len(user_stories),
                "software_flows": len(software_flows),
                "test_cases": len(test_cases),
            },
            "data": {
                "user_stories": user_stories,
                "software_flows": software_flows,
                "test_cases": test_cases,
            },
        }

    finally:
        await conn.close()
