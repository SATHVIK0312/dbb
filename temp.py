import os
import re
import tempfile
from pathlib import Path
from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import utils


def _get_status_color(status: str) -> str:
    colors_map = {
        "SUCCESS": "#10b981", "PASSED": "#10b981",
        "COMPLETED": "#3b82f6",
        "FAILED": "#ef4444", "ERROR": "#f97316",
        "SKIPPED": "#8b5cf6"
    }
    return colors_map.get(status.upper().strip(), "#6b7280")


# Smart path extractor from message text
def extract_script_path_from_message(message: str) -> str:
    if not message:
        return None

    text = str(message)

    # Common patterns
    patterns = [
        r'Stored at:\s*([A-Za-z]:\\.+?\.py)',           # "Stored at: I:\path\to\file.py"
        r'Script path:\s*([A-Za-z]:\\.+?\.[\w]+)',     # "Script path: C:\..."
        r'path[:\s]+([A-Za-z]:\\.+?\.[\w]+)',          # flexible
        r'executed.*?\.py\s*at[:\s]*([A-Za-z]:\\.+?\.py)',
        r'([A-Za-z]:\\[^\s"\'<>|]+\.(py|js|sh|sql|java|xml|json|yaml|yml))',  # direct Windows path
        r'(/[\w/\.-]+/(?:[\w\.-]+/)*[\w\.-]+\.(py|js||sh|sql|java|xml|json|yaml|yml))',  # Linux/macOS
        r'[\'"` ]([A-Za-z]:\\[^\'"<>|]+\.(py|js|sh|sql))[\'"` ]',  # quoted paths
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            path = match.group(1).strip()
            # Clean up any trailing punctuation
            path = re.sub(r'[.,;:"\'\]>]+$', '', path).strip()
            return path

    return None


@app.get("/execution/{execution_id}/pdf")
async def get_execution_pdf(
    execution_id: str,
    current_user: dict = Depends(get_current_any_user)
):
    conn = None
    temp_pdf_path = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        if not execution_id or not execution_id.strip():
            raise HTTPException(status_code=400, detail="Invalid execution ID")

        # Fetch execution
        executions = await conn.execute_fetchall(
            """
            SELECT exeid, testcaseid, scripttype, datestamp, exetime, 
                   message, output, status
            FROM execution WHERE exeid = ?
            """,
            (str(execution_id).strip(),)
        )
        if not executions:
            raise HTTPException(status_code=404, detail="Execution not found")
        execution = executions[0]

        # === Extract script path from message ===
        raw_message = execution["message"] or ""
        script_path = extract_script_path_from_message(raw_message)

        # Also fetch test description
        testcase_rows = await conn.execute_fetchall(
            "SELECT testdesc, projectid FROM testcase WHERE testcaseid = ?",
            (execution["testcaseid"],)
        )
        if not testcase_rows:
            raise HTTPException(status_code=404, detail="Test case not found")
        testcase = testcase_rows[0]
        test_desc = testcase.get("testdesc") or "No description"

        # Project access check
        access = await conn.execute_fetchall(
            "SELECT 1 FROM projectuser WHERE userid = ? AND projectid = ?",
            (userid, testcase["projectid"])
        )
        if not access:
            raise HTTPException(status_code=403, detail="Access denied")

        # === Read actual script file if path was found ===
        script_code = "No script path detected in execution message."
        script_found = False
        script_language = "text"

        if script_path:
            # Normalize path
            script_path = os.path.normpath(script_path.strip())

            # Try common mappings (especially useful in Docker/container environments)
            possible_paths = [
                script_path,  # exact
                script_path.replace("I:\\", "/app/scripts/").replace("\\", "/"),
                script_path.replace("C:\\", "/app/scripts/").replace("\\", "/"),
                script_path.replace("D:\\", "/scripts/").replace("\\", "/"),
                re.sub(r"^[A-Z]:\\projects\\", "/app/scripts/", script_path, flags=re.IGNORECASE),
                re.sub(r"^[A-Z]:\\automation\\", "/scripts/", script_path, flags=re.IGNORECASE),
            ]

            for path_candidate in possible_paths:
                expanded = os.path.expanduser(path_candidate)
                if os.path.isfile(expanded):
                    try:
                        with open(expanded, "r", encoding="utf-8", errors="ignore") as f:
                            script_code = f.read()
                        script_found = True
                        ext = Path(expanded).suffix.lower()
                        script_language = {
                            ".py": "python", ".js": "javascript", ".sh": "bash",
                            ".sql": "sql", ".java": "java", ".xml": "xml",
                            ".json": "json", ".yml": "yaml", ".yaml": "yaml"
                        }.get(ext, "text")
                        script_path = expanded  # show real resolved path
                        break
                    except Exception as e:
                        utils.logger.warning(f"Could not read {expanded}: {e}")

            if not script_found:
                script_code = f"Script file not found on server:\n{script_path}\n\nTried mapping to container paths but file missing."

        # Truncate very long code
        if len(script_code) > 25_000:
            script_code = script_code[:25_000] + "\n\n--- [SOURCE CODE TRUNCATED] ---"

        # === PDF Generation ===
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_pdf_path = temp_file.name
        temp_file.close()

        doc = SimpleDocTemplate(temp_pdf_path, pagesize=letter,
                                rightMargin=0.5*inch, leftMargin=0.5*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle("Title", parent=styles["Heading1"],
                                     fontSize=20, alignment=1, spaceAfter=30,
                                     textColor=colors.HexColor("#1f2937"))

        heading_style = ParagraphStyle("Heading", parent=styles["Heading2"],
                                       fontSize=14, spaceBefore=16, spaceAfter=8,
                                       textColor=colors.HexColor("#374151"))

        label_style = ParagraphStyle("Label", fontName="Helvetica-Bold",
                                     fontSize=10, textColor=colors.HexColor("#4b5563"))

        value_style = ParagraphStyle("Value", fontSize=10,
                                     textColor=colors.HexColor("#1f2937"))

        code_style = ParagraphStyle("Code", fontName="Courier", fontSize=8,
                                    leading=9.5, spaceAfter=2, leftIndent=10,
                                    backColor=colors.HexColor("#f9fafb"),
                                    borderColor=colors.HexColor("#e5e7eb"),
                                    borderWidth=0.5, borderPadding=8)

        content = []

        # Title
        content.append(Paragraph("Test Execution Report", title_style))
        content.append(Spacer(1, 0.3 * inch))

        # Summary
        summary_data = [
            ["Execution ID", str(execution["exeid"])],
            ["Test Case ID", str(execution["testcaseid"])],
            ["Description", test_desc],
            ["Script Type", execution["scripttype"] or "Unknown"],
            ["Date", str(execution["datestamp"])],
            ["Time", str(execution["exetime"])],
            ["Status", f"<font color='{_get_status_color(execution['status'])}'><b>{execution['status']}</b></font>"],
        ]
        table = Table(summary_data, colWidths=[2.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 1, colors.lightgrey),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f3f4f6")),
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 8),
        ]))
        content.append(Paragraph("Execution Summary", heading_style))
        content.append(table)
        content.append(Spacer(1, 0.4 * inch))

        # Message
        clean_message = raw_message.split("Stored at:")[-1].split("path:")[-1] if "Stored at:" in raw_message or "path:" in raw_message else raw_message
        content.append(Paragraph("Execution Message", heading_style))
        content.append(Paragraph(clean_message.replace("\n", "<br/>"), value_style))
        content.append(Spacer(1, 0.3 * inch))

        # Output
        content.append(Paragraph("Console Output", heading_style))
        output = execution["output"] or "No output"
        if len(output) > 10_000:
            output = output[:10_000] + "\n\n... [TRUNCATED]"
        for i, line in enumerate(output.splitlines()):
            if i > 350:
                content.append(Paragraph("... [MORE OUTPUT TRUNCATED]", code_style))
                break
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            content.append(Paragraph(line or "&nbsp;", code_style))
        content.append(Spacer(1, 0.4 * inch))

        # Source Code
        content.append(Paragraph("Test Script Source Code", heading_style))
        if script_found:
            content.append(Paragraph(f"<i>Resolved path: {script_path}</i>", value_style))
        else:
            content.append(Paragraph(f"<i>Warning: Could not load script file</i>", value_style))
        content.append(Spacer(1, 8))

        line_count = 0
        for line in script_code.splitlines():
            if line_count >= 500:
                content.append(Paragraph("--- [CODE TOO LONG - TRUNCATED] ---", code_style))
                break
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            content.append(Paragraph(line or "&nbsp;", code_style))
            line_count += 1

        doc.build(content)

        return FileResponse(
            temp_pdf_path,
            media_type="application/pdf",
            filename=f"execution_{execution_id}_report.pdf",
            headers={"Content-Disposition": f"attachment; filename=execution_{execution_id}_report.pdf"}
        )

    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"PDF generation failed for {execution_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate PDF")
    finally:
        if conn:
            await db.release_db_connection(conn)
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try: os.unlink(temp_pdf_path)
            except: pass
