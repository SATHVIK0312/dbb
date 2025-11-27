# -----------------------------
# 2. Validate access & test case (JSON array supported)
# -----------------------------
cursor = await conn.execute(
    "SELECT projectid FROM testcase WHERE testcaseid = ?",
    (testcase_id,)
)
tc_project = await cursor.fetchone()

if not tc_project:
    await websocket.send_text(json.dumps({"error": "Test case not found", "status": "FAILED"}))
    await websocket.close()
    return

# JSON array format supported
cursor = await conn.execute(
    """
    SELECT 1 
    FROM projectuser 
    WHERE userid = ?
      AND json_extract(projectid, '$') LIKE ?
    """,
    (userid, f'%"{tc_project["projectid"]}"%')
)

access = await cursor.fetchone()

if not access:
    await websocket.send_text(json.dumps({"error": "Unauthorized", "status": "FAILED"}))
    await websocket.close()
    return
