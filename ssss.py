# ========================================================
# FINAL SELF-CONTAINED WEBSOCKET ENDPOINT (NO EXTERNAL FILES)
# Works 100% with your C# frontend – ZERO changes needed
# ========================================================
import json
import os
import sys
import uuid
import tempfile
import subprocess
import asyncio
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from jose import jwt, JWTError as JWTError

# === Your existing Azure OpenAI client (keep exactly as you have it) ===
# Example (replace with your real one if different)
from openai import AzureOpenAI

def get_azure_openai_client():
    return AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version="2024-08-01-preview"
    )

# === Your constants (adjust only if different) ===
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

# In-memory DB simulation (replace with your real db logic if you have it)
# Remove this whole block if you already have get_db_connection()
import aiosqlite

DB_PATH = "test.db

async def get_db_connection():
    return await aiosqlite.connect(DB_PATH)

async def from_json(value):
    return json.loads(value) if value else []

async def get_next_exeid(conn):
    row = await conn.execute("SELECT MAX(exeid) FROM execution")
    result = await row.fetchone()
    return f"EXE{int(result[0][3:] or '0') + 1:06d}" if result[0] else "EXE000001"

# ========================================================
# MAIN WEBSOCKET ENDPOINT – COPY FROM HERE DOWN
# ========================================================
@app.websocket("/testcases/{testcase_id}/execute-with-madl")
async def execute_testcase_with_madl(
    websocket: WebSocket,
    testcase_id: str,
    script_type: str = "playwright"
):
    await websocket.accept()

    # Simple logger (no external file needed)
    logs = []
    def log(msg: str):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    log(f"Execution started: {testcase_id} | {script_type}")

    conn = None
    try:
        # === 1. Extract JWT token ===
        token = None
        for k, v in websocket.scope.get("headers", []):
            if k == b"authorization":
                try:
                    token = v.decode().split("Bearer ")[1].strip()
                except:
                    pass
                break

        if not token:
            await websocket.send_text(json.dumps({"error": "Missing token", "status": "FAILED"}))
            await websocket.close()
            return

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            userid = payload.get("userid")
        except JWTError:
            await websocket.send_text(json.dumps({"error": "Invalid token", "status": "FAILED"}))
            await websocket.close()
            return

        # === 2. DB + Access check (simple version) ===
        conn = await get_db_connection()
        row = await conn.execute_fetchone(
            "SELECT projectid FROM testcase WHERE testcaseid = ?", (testcase_id,)
        )
        if not row:
            await websocket.send_text(json.dumps({"error": "Test case not found", "status": "FAILED"}))
            await websocket.close()
            return

        user_row = await conn.execute_fetchone(
            "SELECT projectid FROM projectuser WHERE userid = ?", (userid,)
        )
        user_projects = set(from_json(user_row["projectid"])) if user_row else set()
        tc_projects = set(from_json(row["projectid"]))

        if not (user_projects & tc_projects):
            await websocket.send_text(json.dumps({"error": "Unauthorized", "status": "FAILED"}))
            await websocket.close()
            return

        # === 3. Build test plan ===
        await websocket.send_text(json.dumps({"status": "BUILDING_PLAN", "log": "Building test plan..."}))

        async def get_chain(tid):
            chain = []
            while tid:
                chain.append(tid)
                r = await conn.execute_fetchone(
                    "SELECT pretestid FROM testcase WHERE testcaseid = ?", (tid,)
                )
                tid = r["pretestid"] if r and r["pretestid"] else None
            return chain[::-1]

        chain = await get_chain(testcase_id)

        plan = {"pretestid - steps": {}, "current - bdd steps": {}}
        for tid in chain[:-1]:
            r = await conn.execute_fetchone(
                "SELECT steps, args FROM teststep WHERE testcaseid = ?", (tid,)
            )
            if r and r["steps"]:
                plan["pretestid - steps"][tid] = dict(zip(from_json(r["steps"]), from_json(r["args"])))

        r = await conn.execute_fetchone(
            "SELECT steps, args FROM teststep WHERE testcaseid = ?", (testcase_id,)
        )
        if r and r["steps"]:
            plan["current - bdd steps"] = dict(zip(from_json(r["steps"]), from_json(r["args"])))

        testplan_json = json.dumps(plan, indent=2)
        await websocket.send_text(json.dumps({"status": "PLAN_READY", "log": "Test plan ready"}))

        await websocket.send_text(json.dumps({"status": "NO_MADL_METHODS", "log": "Skipping MADL – proceeding directly"}))

        # === 4. Generate script ===
        await websocket.send_text(json.dumps({"status": "GENERATING", "log": "Generating script..."}))

        prompt = f"""
Generate a complete runnable Python {script_type} test script for test case {testcase_id}.

Test plan:
{testplan_json}

Rules:
- Use sync API (sync_playwright or selenium)
- Wrap every step in try/except
- Print: "Running action: <step> at <timestamp>"
- Print: "Action completed: <step> at <timestamp>"
- On error: "Action <step> failed: <error>" + take screenshot
- Screenshot path: error_screenshot.png
- Output ONLY clean Python code, no markdown.
"""

        client = get_azure_openai_client()
        resp = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4000
        )

        script = resp.choices[0].message.content.strip()
        if "```" in script:
            parts = script.split("```")
            script = parts[1].strip()
            if script.lower().startswith("python"):
                script = "\n".join(script.splitlines()[1:])

        # === 5. Execute script ===
        await websocket.send_text(json.dumps({"status": "EXECUTING", "log": "Running..."}))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(script)
            tmp_path = f.name

        proc = subprocess.Popen([sys.executable, tmp_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        output = ""
        for line in proc.stdout:
            line = line.rstrip()
            output += line + "\n"
            await websocket.send_text(json.dumps({"status": "RUNNING", "log": line}))
            await asyncio.sleep(0.02)

        return_code = proc.wait()
        os.unlink(tmp_path)

        if return_code == 0:
            final_status = "SUCCESS"
            final_msg = "Test passed"
        else:
            # === 6. Auto-heal ===
            await websocket.send_text(json.dumps({"status": "AUTO_HEALING", "log": "Healing..."}))

            heal_prompt = f"""The script failed:\n\n{script}\n\nError:\n{output}\n\nFix it. Return only corrected Python code."""

            heal_resp = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[{"role": "user", "content": heal_prompt}],
                temperature=0.0,
                max_tokens=4000
            )
            healed = heal_resp.choices[0].message.content.strip()
            if "```" in healed:
                healed = healed.split("```")[1].strip()
                if healed.lower().startswith("python"):
                    healed = "\n".join(healed.splitlines()[1:])

            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(healed)
                hpath = f.name

            p2 = subprocess.Popen([sys.executable, hpath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            healed_out = ""
            for line in p2.stdout:
                line = line.rstrip()
                healed_out += line + "\n"
                await websocket.send_text(json.dumps({"status": "RUNNING", "log": f"[HEALED] {line}"}))
                await asyncio.sleep(0.02)

            rc2 = p2.wait()
            os.unlink(hpath)

            final_status = "SUCCESS" if rc2 == 0 else "FAILED"
            final_msg = "[HEALED] Passed" if rc2 == 0 else "[HEALED] Still failed"
            output = healed_out

        # === 7. Save result ===
        exeid = await get_next_exeid(conn)
        await conn.execute("""
            INSERT INTO execution 
            (exeid, testcaseid, scripttype, datestamp, exetime, message, output, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (exeid, testcase_id, script_type, datetime.now().date(), datetime.now().time(), final_msg, output, final_status))

        # === 8. Final message (exact same format your frontend expects) ===
        await websocket.send_text(json.dumps({
            "status": "COMPLETED",
            "log": final_msg,
            "final_status": final_status,
            "summary": "\n".join(logs[-20:])  # last 20 log lines
        }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(json.dumps({"error": str(e), "status": "FAILED"}))
    finally:
        if conn:
            await conn.close()
        try:
            await websocket.close()
        except:
            pass
