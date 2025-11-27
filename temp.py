# --- FIXED JSON ARRAY MATCHING ---
cur = await conn.execute(
    """
    SELECT 1
    FROM projectuser
    WHERE userid = ?
      AND json_extract(projectid, '$') LIKE ?
    """,
    (userid, f'%"{tc_project}"%')
)
access = await cur.fetchone()

if not access:
    await websocket.send_text(json.dumps({"error": "Unauthorized", "status": "FAILED"}))
    await websocket.close()
    return
