# =========================================================
# IMPORTS
# =========================================================
import os
import io
import json
import sqlite3
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

# ---------- File parsing ----------
import fitz  # PyMuPDF
from docx import Document
import openpyxl

# ---------- Azure OpenAI ----------
from openai import AzureOpenAI

# =========================================================
# FASTAPI APP
# =========================================================
app = FastAPI(title="Document Intelligence API (No ORM)")

# =========================================================
# DATABASE (sqlite3 – standard library)
# =========================================================
DB_PATH = "document_ai.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# =========================================================
# CREATE TABLES (ON STARTUP)
# =========================================================
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        is_software_related INTEGER NOT NULL,
        reason TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_stories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        story TEXT,
        FOREIGN KEY(document_id) REFERENCES documents(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS software_flows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        step TEXT,
        FOREIGN KEY(document_id) REFERENCES documents(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS test_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        test_case_id TEXT UNIQUE,
        description TEXT,
        pre_req_id TEXT,
        pre_req_desc TEXT,
        tags TEXT,
        steps TEXT,
        arguments TEXT,
        FOREIGN KEY(document_id) REFERENCES documents(id)
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================================================
# PYDANTIC SCHEMAS (ONLY SCHEMAS, NO ORM)
# =========================================================
class UserStorySchema(BaseModel):
    story: str


class SoftwareFlowSchema(BaseModel):
    step: str


class TestCaseSchema(BaseModel):
    test_case_id: str
    description: str
    pre_req_id: Optional[str]
    pre_req_desc: Optional[str]
    tags: Optional[str]
    steps: Optional[str]
    arguments: Optional[str]


class DocumentResponseSchema(BaseModel):
    document_id: int
    filename: str
    is_software_related: bool
    reason: Optional[str]
    test_cases_generated: int

# =========================================================
# FILE TEXT EXTRACTION
# =========================================================
def extract_text(file: UploadFile) -> str:
    content = file.file.read()

    if file.filename.endswith(".pdf"):
        doc = fitz.open(stream=content, filetype="pdf")
        return "\n".join(p.get_text() for p in doc)

    if file.filename.endswith(".docx"):
        document = Document(io.BytesIO(content))
        return "\n".join(p.text for p in document.paragraphs)

    if file.filename.endswith(".xlsx"):
        wb = openpyxl.load_workbook(io.BytesIO(content))
        text = ""
        for sheet in wb:
            for row in sheet.iter_rows(values_only=True):
                text += " ".join(str(c) for c in row if c) + "\n"
        return text

    raise HTTPException(status_code=400, detail="Unsupported file type")

# =========================================================
# AZURE OPENAI CLIENT (YOUR REQUIRED STYLE)
# =========================================================
def get_azure_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version="2024-02-15-preview"
    )

# =========================================================
# AI ANALYSIS
# =========================================================
def analyze_with_ai(text: str) -> dict:
    client = get_azure_openai_client()

    prompt = f"""
You are a Senior Software Business Analyst and QA Architect.

ONLY return valid JSON.

If NOT software-related:
{{"is_software_related": false, "reason": "..."}}

If software-related:
{{
  "is_software_related": true,
  "reason": "...",
  "user_stories": ["Feature: ... | Aim: ..."],
  "software_flow": ["Step 1", "Step 2"],
  "test_cases": [
    {{
      "test_case_description": "...",
      "tags": ["Regression"],
      "test_steps": ["Step 1", "Step 2"],
      "arguments": ["arg1"]
    }}
  ]
}}

DOCUMENT:
\"\"\"{text}\"\"\"
"""

    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=[{"role": "system", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=4000,
        top_p=0.95,
        timeout=300
    )

    return json.loads(response.choices[0].message.content)

# =========================================================
# GTC ID GENERATOR (GLOBAL, SQLITE)
# =========================================================
def generate_gtc_id(conn: sqlite3.Connection) -> str:
    cur = conn.cursor()
    cur.execute("SELECT test_case_id FROM test_cases ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()

    if not row:
        return "GTC001"

    last_num = int(row["test_case_id"].replace("GTC", ""))
    return f"GTC{last_num + 1:03d}"

# =========================================================
# API ENDPOINT
# =========================================================
@app.post("/analyze-document")
async def analyze_document(file: UploadFile = File(...)):
    # -------------------------------------------------
    # 1. Extract text from file
    # -------------------------------------------------
    text = extract_text(file)

    # -------------------------------------------------
    # 2. Call Azure OpenAI
    # -------------------------------------------------
    ai_result = analyze_with_ai(text)

    # -------------------------------------------------
    # 3. Open async DB connection
    # -------------------------------------------------
    conn = await get_db_connection()

    try:
        async with conn.cursor() as cur:
            # -------------------------------------------------
            # 4. Insert document row
            # -------------------------------------------------
            await cur.execute(
                """
                INSERT INTO documents (filename, is_software_related, reason)
                VALUES (?, ?, ?)
                """,
                (
                    file.filename,
                    int(ai_result["is_software_related"]),
                    ai_result["reason"]
                )
            )

            document_id = cur.lastrowid

            # -------------------------------------------------
            # 5. If NOT software-related → stop here
            # -------------------------------------------------
            if not ai_result["is_software_related"]:
                await conn.commit()
                return {
                    "document_id": document_id,
                    "is_software_related": False,
                    "reason": ai_result["reason"],
                    "test_cases_generated": 0
                }

            # -------------------------------------------------
            # 6. Insert user stories
            # -------------------------------------------------
            for story in ai_result.get("user_stories", []):
                await cur.execute(
                    """
                    INSERT INTO user_stories (document_id, story)
                    VALUES (?, ?)
                    """,
                    (document_id, story)
                )

            # -------------------------------------------------
            # 7. Insert software flow steps
            # -------------------------------------------------
            for step in ai_result.get("software_flow", []):
                await cur.execute(
                    """
                    INSERT INTO software_flows (document_id, step)
                    VALUES (?, ?)
                    """,
                    (document_id, step)
                )

            # -------------------------------------------------
            # 8. Insert test cases with GTC IDs
            # -------------------------------------------------
            test_case_count = 0

            for tc in ai_result.get("test_cases", []):
                # Fetch last GTC id
                await cur.execute(
                    """
                    SELECT test_case_id
                    FROM test_cases
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
                row = await cur.fetchone()

                if row is None:
                    gtc_id = "GTC001"
                else:
                    last_num = int(row["test_case_id"].replace("GTC", ""))
                    gtc_id = f"GTC{last_num + 1:03d}"

                await cur.execute(
                    """
                    INSERT INTO test_cases
                    (document_id, test_case_id, description,
                     pre_req_id, pre_req_desc,
                     tags, steps, arguments)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        gtc_id,
                        tc["test_case_description"],
                        "USER_INPUT",
                        "USER_INPUT",
                        ",".join(tc.get("tags", [])),
                        "\n".join(tc.get("test_steps", [])),
                        ",".join(tc.get("arguments", []))
                    )
                )

                test_case_count += 1

            # -------------------------------------------------
            # 9. Commit everything
            # -------------------------------------------------
            await conn.commit()

            return {
                "document_id": document_id,
                "is_software_related": True,
                "reason": ai_result["reason"],
                "test_cases_generated": test_case_count
            }

    finally:
        await conn.close()
