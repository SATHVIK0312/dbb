# Load project list for user
cur = await conn.execute("SELECT projectid FROM projectuser WHERE userid = ?", (userid,))
row = await cur.fetchone()

if not row:
    await websocket.send_text(json.dumps({"error": "Unauthorized", "status": "FAILED"}))
    await websocket.close()
    return

raw = row["projectid"]

# Convert Python-style list string -> JSON
fixed = raw.replace("'", '"')

try:
    project_list = json.loads(fixed)
except:
    # fallback manual parsing
    cleaned = fixed.replace("[","").replace("]","")
    project_list = [x.strip(' "')
                    for x in cleaned.split(",")]

# CHECK ACCESS
if tc_project not in project_list:
    await websocket.send_text(json.dumps({"error": "Unauthorized", "status": "FAILED"}))
    await websocket.close()
    return
