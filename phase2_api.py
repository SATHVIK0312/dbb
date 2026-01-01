# =========================================================
# IMPORTS & LIBRARIES
# =========================================================
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from typing import List, Optional
import tempfile
import os
import json

# ---------- File Parsing ----------
import fitz  # PyMuPDF
import docx
import openpyxl

# ---------- Azure OpenAI ----------
from openai import AzureOpenAI

# =========================================================
# FASTAPI APP INIT
# =========================================================
app = FastAPI(title="Document Intelligence API")

# =========================================================
# DATABASE CONFIGURATION (SQLITE)
# =========================================================
DATABASE_URL = "sqlite:///./document_intelligence.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# =========================================================
# DATABASE MODELS
# =========================================================
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    is_software_related = Column(Integer)
    reason = Column(Text)

    user_stories = relationship("UserStory", back_populates="document")
    flows = relationship("SoftwareFlow", back_populates="document")
    test_cases = relationship("TestCase", back_populates="document")


class UserStory(Base):
    __tablename__ = "user_stories"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    story = Column(Text)

    document = relationship("Document", back_populates="user_stories")


class SoftwareFlow(Base):
    __tablename__ = "software_flows"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    step = Column(Text)

    document = relationship("Document", back_populates="flows")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))

    test_case_id = Column(String, unique=True, index=True)
    description = Column(Text)

    pre_req_id = Column(String, nullable=True)
    pre_req_desc = Column(Text, nullable=True)

    tags = Column(Text)
    steps = Column(Text)
    arguments = Column(Text)

    document = relationship("Document", back_populates="test_cases")


Base.metadata.create_all(bind=engine)

# =========================================================
# DEPENDENCY: DATABASE SESSION
# =========================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def generate_gtc_id(index: int) -> str:
    """Generate sequential GTC IDs"""
    return f"GTC{str(index).zfill(3)}"


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
# AZURE OPENAI CLIENT & ANALYSIS
# =========================================================
AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com/"
AZURE_OPENAI_KEY = "YOUR_AZURE_OPENAI_KEY"
AZURE_OPENAI_DEPLOYMENT = "gpt-4o"

client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2024-02-15-preview"
)


def analyze_with_ai(text: str) -> dict:
    """Send document text to Azure OpenAI for analysis"""
    prompt = f"""
You are a Senior Software Business Analyst and QA Architect.

Return ONLY valid JSON.

If NOT software-related:
{{"is_software_related": false, "reason": "..." }}

If software-related:
{{
  "is_software_related": true,
  "reason": "...",
  "user_stories": ["Feature: ... | Aim: ..."],
  "software_flow": ["Step 1: ...", "Step 2: ..."],
  "test_cases": [
    {{
      "test_case_description": "...",
      "pre_requisite_test_id": null,
      "pre_requisite_test_description": null,
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
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "Strict JSON only"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return json.loads(response.choices[0].message.content)

# =========================================================
# API ENDPOINT
# =========================================================
@app.post("/analyze-document")
async def analyze_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["pdf", "docx", "xlsx"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    try:
        extracted_text = extract_text(temp_path, ext)
        if len(extracted_text) < 100:
            raise HTTPException(status_code=400, detail="Document content too small")

        result = analyze_with_ai(extracted_text)

        document = Document(
            filename=file.filename,
            is_software_related=int(result["is_software_related"]),
            reason=result["reason"]
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        if not result["is_software_related"]:
            return {
                "message": "Not software-related",
                "reason": result["reason"]
            }

        for us in result["user_stories"]:
            db.add(UserStory(document_id=document.id, story=us))

        for step in result["software_flow"]:
            db.add(SoftwareFlow(document_id=document.id, step=step))

        for idx, tc in enumerate(result["test_cases"], start=1):
            db.add(TestCase(
                document_id=document.id,
                test_case_id=generate_gtc_id(idx),
                description=tc["test_case_description"],
                pre_req_id=tc["pre_requisite_test_id"],
                pre_req_desc=tc["pre_requisite_test_description"],
                tags=",".join(tc["tags"]),
                steps="\n".join(tc["test_steps"]),
                arguments=",".join(tc["arguments"]) if tc["arguments"] else None
            ))

        db.commit()

        return {
            "message": "Document processed successfully",
            "document_id": document.id,
            "test_cases_generated": len(result["test_cases"])
        }

    finally:
        os.remove(temp_path)


==================================================================
==================================================================

CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    is_software_related INTEGER NOT NULL, -- 1 = true, 0 = false
    reason TEXT
);


CREATE TABLE user_stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    story TEXT NOT NULL,
    FOREIGN KEY (document_id)
        REFERENCES documents (id)
        ON DELETE CASCADE
);


CREATE TABLE software_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    step TEXT NOT NULL,
    FOREIGN KEY (document_id)
        REFERENCES documents (id)
        ON DELETE CASCADE
);



CREATE TABLE test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,

    test_case_id TEXT NOT NULL UNIQUE,   -- GTC001, GTC002, ...
    description TEXT NOT NULL,

    pre_req_id TEXT,
    pre_req_desc TEXT,

    tags TEXT,        -- comma-separated
    steps TEXT,       -- newline-separated
    arguments TEXT,   -- comma-separated

    FOREIGN KEY (document_id)
        REFERENCES documents (id)
        ON DELETE CASCADE
);



===================================================================
===================================================================

class TestCaseSchema(BaseModel):
    test_case_id: str
    description: str
    pre_req_id: Optional[str]
    pre_req_desc: Optional[str]
    tags: Optional[str]
    steps: Optional[str]
    arguments: Optional[str]

    model_config = {
        "from_attributes": True  # REQUIRED in Pydantic v2
    }


class UserStorySchema(BaseModel):
    story: str

    model_config = {
        "from_attributes": True
    }


class SoftwareFlowSchema(BaseModel):
    step: str

    model_config = {
        "from_attributes": True
    }

class DocumentResponseSchema(BaseModel):
    id: int
    filename: str
    is_software_related: int
    reason: Optional[str]
    user_stories: List[UserStorySchema] = []
    flows: List[SoftwareFlowSchema] = []
    test_cases: List[TestCaseSchema] = []

    model_config = {
        "from_attributes": True
    }

