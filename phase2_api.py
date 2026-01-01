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

class TestCaseSchema(BaseModel):
    test_case_id: str
    description: str
    pre_req_id: Optional[str]
    pre_req_desc: Optional[str]
    tags: Optional[str]
    steps: Optional[str]
    arguments: Optional[str]

    model_config = {"from_attributes": True}


class DocumentResponseSchema(BaseModel):
    document_id: int
    is_software_related: bool
    reason: str
    test_cases_generated: int

class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    is_software_related = Column(Integer)
    reason = Column(Text)

    user_stories = relationship("UserStoryModel", cascade="all, delete")
    flows = relationship("SoftwareFlowModel", cascade="all, delete")
    test_cases = relationship("TestCaseModel", cascade="all, delete")


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
def analyze_with_ai(text: str) -> dict:
    client = get_azure_openai_client()

    prompt = f"""
You are a Senior Software Business Analyst and QA Architect.

ONLY return valid JSON.

If the document is NOT related to software requirements,
return:
{{"is_software_related": false, "reason": "..." }}

If software-related, return:
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
# TEST CASE ID GENERATOR (GLOBAL UNIQUE)
# =========================================================
def generate_gtc_id(db: Session) -> str:
    last = db.query(TestCaseModel).order_by(TestCaseModel.id.desc()).first()
    if not last:
        return "GTC001"
    num = int(last.test_case_id.replace("GTC", "")) + 1
    return f"GTC{num:03d}"





# =========================================================
# API ENDPOINT
# =========================================================
@app.post("/analyze-document", response_model=DocumentResponseSchema)
async def analyze_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    text = extract_text(file)
    result = analyze_with_ai(text)

    document = DocumentModel(
        filename=file.filename,
        is_software_related=int(result["is_software_related"]),
        reason=result["reason"]
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    if not result["is_software_related"]:
        return DocumentResponseSchema(
            document_id=document.id,
            is_software_related=False,
            reason=result["reason"],
            test_cases_generated=0
        )

    for story in result["user_stories"]:
        db.add(UserStoryModel(document_id=document.id, story=story))

    for step in result["software_flow"]:
        db.add(SoftwareFlowModel(document_id=document.id, step=step))

    count = 0
    for tc in result["test_cases"]:
        tc_id = generate_gtc_id(db)
        db.add(TestCaseModel(
            document_id=document.id,
            test_case_id=tc_id,
            description=tc["test_case_description"],
            pre_req_id="USER_INPUT",
            pre_req_desc="USER_INPUT",
            tags=",".join(tc.get("tags", [])),
            steps="\n".join(tc.get("test_steps", [])),
            arguments=",".join(tc.get("arguments", []))
        ))
        count += 1

    db.commit()

    return DocumentResponseSchema(
        document_id=document.id,
        is_software_related=True,
        reason=result["reason"],
        test_cases_generated=count
    )


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










========================================

# =========================================================
# SQLALCHEMY ORM MODELS (DB LAYER ONLY)
# =========================================================

class DocumentORM(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    is_software_related: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)

    user_stories: Mapped[List["UserStoryORM"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan"
    )
    flows: Mapped[List["SoftwareFlowORM"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan"
    )
    test_cases: Mapped[List["TestCaseORM"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan"
    )


class UserStoryORM(Base):
    __tablename__ = "user_stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE")
    )
    story: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped["DocumentORM"] = relationship(back_populates="user_stories")


class SoftwareFlowORM(Base):
    __tablename__ = "software_flows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE")
    )
    step: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped["DocumentORM"] = relationship(back_populates="flows")


class TestCaseORM(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE")
    )

    test_case_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    pre_req_id: Mapped[Optional[str]] = mapped_column(String)
    pre_req_desc: Mapped[Optional[str]] = mapped_column(Text)

    tags: Mapped[Optional[str]] = mapped_column(Text)
    steps: Mapped[Optional[str]] = mapped_column(Text)
    arguments: Mapped[Optional[str]] = mapped_column(Text)

    document: Mapped["DocumentORM"] = relationship(back_populates="test_cases")

# =========================================================
# PYDANTIC SCHEMAS (API LAYER ONLY)
# =========================================================

class UserStorySchema(BaseModel):
    id: Optional[int]
    story: str

    model_config = {"from_attributes": True}


class SoftwareFlowSchema(BaseModel):
    id: Optional[int]
    step: str

    model_config = {"from_attributes": True}


class TestCaseSchema(BaseModel):
    test_case_id: str
    description: str
    pre_req_id: Optional[str]
    pre_req_desc: Optional[str]
    tags: Optional[str]
    steps: Optional[str]
    arguments: Optional[str]

    model_config = {"from_attributes": True}


class DocumentResponseSchema(BaseModel):
    document_id: int
    filename: str
    is_software_related: bool
    reason: Optional[str]
    user_stories: List[UserStorySchema] = []
    flows: List[SoftwareFlowSchema] = []
    test_cases: List[TestCaseSchema] = []

    model_config = {"from_attributes": True}

