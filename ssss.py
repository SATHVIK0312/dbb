# -----------------------------
# VALIDATE TESTCASE + ACCESS
# -----------------------------

# 1. Validate testcase exists and get its project id
cur = await conn.execute(
    "SELECT projectid FROM testcase WHERE testcaseid = ?", 
    (testcase_id,)
)
row = await cur.fetchone()

if not row:
    await websocket.send_text(json.dumps({"error": "Test case not found", "status": "FAILED"}))
    await websocket.close()
    return

tc_project = row[0]   # e.g. "P001"

# 2. Load project list for user
cur = await conn.execute(
    "SELECT projectid FROM projectuser WHERE userid = ?", 
    (userid,)
)
row = await cur.fetchone()

if not row:
    await websocket.send_text(json.dumps({"error": "Unauthorized", "status": "FAILED"}))
    await websocket.close()
    return

raw = row[0]   # stored as "['P001','P002']" or similar

# 3. Convert Python-style list string to real list
fixed = raw.replace("'", '"')

try:
    project_list = json.loads(fixed)
except:
    cleaned = fixed.replace("[", "").replace("]", "")
    project_list = [
        x.strip(' "') 
        for x in cleaned.split(",") 
        if x.strip()
    ]

# 4. Access check
if str(tc_project) not in map(str, project_list):
    await websocket.send_text(json.dumps({"error": "Unauthorized", "status": "FAILED"}))
    await websocket.close()
    return
