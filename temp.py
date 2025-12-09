import os
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

# Status color mapping
def _get_status_color(status: str) -> str:
    colors_map = {
        "SUCCESS": "#10b981",
        "COMPLETED": "#3b82f6",
        "PASSED": "#10b981",
        "FAILED": "#ef4444",
        "ERROR": "#f97316",
        "SKIPPED": "#8b5cf6"
    }
    return colors_map.get(status.upper(), "#6b7280")

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

        # Fetch execution record
        execution_rows = await conn.execute_fetchall(
            """
            SELECT exeid, testcaseid, scripttype, datestamp, exetime, 
                   message, output, status
            FROM execution
            WHERE exeid = ?
            """,
            (str(execution_id).strip(),)
        )

        if not execution_rows:
            raise HTTPException(status_code=404, detail="Execution record not found")

        execution = execution_rows[0]

        # Fetch testcase details including scriptpath and description
        testcase_rows = await conn.execute_fetchall(
            """
            SELECT tc.testdesc, tc.scriptpath, tc.projectid
            FROM testcase tc
            WHERE tc.testcaseid = ?
            """,
            (execution["testcaseid"],)
        )

        if not testcase_rows:
            raise HTTPException(status_code=404, detail="Test case not found")

        testcase = testcase_rows[0]
        projectid = testcase["projectid"]
        test_desc = testcase.get("testdesc") or "No description provided"
        script_path = testcase.get("scriptpath")  # This is the file path on disk

        # Authorization: Check if user has access to the project
        access_rows = await conn.execute_fetchall(
            "SELECT 1 FROM projectuser WHERE userid = ? AND projectid = ?",
            (userid, projectid)
        )
        if not access_rows:
            raise HTTPException(status_code=403, detail="You are not authorized to view this execution")

        # Resolve and read the actual script file
        script_code = "Script file path not specified in test case."
        script_language = "text"
        script_found = False

        if script_path:
            script_path = str(script_path).strip()
            # Common base directories to check (adjust as per your deployment)
            base_dirs = [
                "/app/scripts",
                "/scripts",
                "./scripts",
                "/var/scripts",
                os.path.dirname(os.path.abspath(__file__)),  # fallback: current dir
                os.getcwd()
            ]

            candidate_paths = [script_path]
            for base in base_dirs:
                candidate_paths.append(os.path.join(base, script_path))
                candidate_paths.append(os.path.join(base, "tests", script_path))

            for full_path in candidate_paths:
                expanded = os.path.expanduser(full_path)
                if os.path.isfile(expanded):
                    try:
                        with open(expanded, "r", encoding="utf-8") as f:
                            script_code = f.read()
                        script_found = True
                        suffix = Path(expanded).suffix.lower()
                        script_language = {
                            ".py": "python",
                            ".js": "javascript",
                            ".sh": "bash",
                            ".sql": "sql",
                            ".java": "java",
                            ".xml": "xml",
                            ".json": "json",
                            ".yml": "yaml",
                            ".yaml": "yaml",
                            ".html": "html",
                        }.get(suffix, "text")
                        break
                    except Exception as e:
                        utils.logger.warning(f"Failed to read script {expanded}: {e}")

            if not script_found:
                script_code = f"Script file not found on server.\nLooked in:\n" + "\n".join(candidate_paths[:6])
                if len(candidate_paths) > 6:
                    script_code += "\n... (and more)"

        # Truncate extremely long scripts
        if len(script_code) > 20_000:
            script_code = script_code[:20_000] + "\n\n--- [SOURCE CODE TRUNCATED - TOO LARGE FOR PDF] ---"

        # Create temporary PDF
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_pdf_path = temp_file.name
        temp_file.close()

        doc = SimpleDocTemplate(
            temp_pdf_path,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Heading1"],
            fontSize=20, spaceAfter=20, alignment=1, textColor=colors.HexColor("#1f2937")
        )
        heading_style = ParagraphStyle(
            "Heading", parent=styles["Heading2"],
            fontSize=14, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor("#374151")
        )
        label_style = ParagraphStyle(
            "Label", parent=styles["Normal"],
            fontSize=10, fontName="Helvetica-Bold", textColor=colors.HexColor("#4b5563")
        )
        value_style = ParagraphStyle(
            "Value", parent=styles["Normal"],
            fontSize=10, textColor=colors.HexColor("#1f2937")
        )
        code_style = ParagraphStyle(
            "Code",
            fontName="Courier",
            fontSize=8,
            leading=9.5,
            spaceAfter=3,
            leftIndent=12,
            textColor=colors.HexColor("#1f2937"),
            backColor=colors.HexColor("#f9fafb"),
            borderColor=colors.HexColor("#e5e7eb"),
            borderWidth=0.5,
            borderPadding=8,
            borderRadius=4,
        )

        content = []

        # Title
        content.append(Paragraph("Test Execution Report", title_style))
        content.append(Spacer(1, 0.3 * inch))

        # Summary Table
        summary_data = [
            ["Execution ID", str(execution["exeid"])],
            ["Test Case ID", str(execution["testcaseid"])],
            ["Description", test_desc],
            ["Script Type", execution["scripttype"] or "N/A"],
            ["Execution Date", str(execution["datestamp"])],
            ["Execution Time", str(execution["exetime"])],
            ["Status", f"<font color='{_get_status_color(execution['status'])}'><b>{execution['status']}</b></font>"],
        ]

        summary_table = Table(summary_data, colWidths=[2.5 * inch, 4.5 * inch])
        summary_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, colors.lightgrey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        content.append(Paragraph("Execution Summary", heading_style))
        content.append(summary_table)
        content.append(Spacer(1, 0.4 * inch))

        # Execution Message
        content.append(Paragraph("Execution Message", heading_style))
        message = execution["message"] or "No message recorded."
        content.append(Paragraph(message.replace("\n", "<br/>"), value_style))
        content.append(Spacer(1, 0.3 * inch))

        # Console Output
        content.append(Paragraph("Console Output / Logs", heading_style))
        output = execution["output"] or "No output captured."
        if len(output) > 8000:
            output = output[:8000] + "\n\n... [OUTPUT TRUNCATED] ..."
        for i, line in enumerate(output.splitlines()):
            if i >= 300:
                content.append(Paragraph("... [MORE OUTPUT TRUNCATED]", code_style))
                break
            safe_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            content.append(Paragraph(safe_line or "&nbsp;", code_style))
        content.append(Spacer(1, 0.4 * inch))

        # Test Script Source Code
        content.append(Paragraph("Test Script Source Code", heading_style))
        if script_found:
            lang_note = f" ({script_language.upper()})" if script_language != "text" else ""
            content.append(Paragraph(f"<i>File: {script_path}{lang_note}</i>", value_style))
        else:
            content.append(Paragraph("<i>Warning: Script file could not be loaded</i>", value_style))

        content.append(Spacer(1, 8))

        line_count = 0
        max_lines = 500
        for line in script_code.splitlines():
            if line_count >= max_lines:
                content.append(Paragraph("--- [CODE TRUNCATED - TOO LONG] ---", code_style))
                break
            safe_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if not safe_line.strip():
                safe_line = "&nbsp;"
            content.append(Paragraph(safe_line, code_style))
            line_count += 1

        # Build PDF
        doc.build(content)

        # Return file
        return FileResponse(
            temp_pdf_path,
            media_type="application/pdf",
            filename=f"execution_{execution_id}_report.pdf",
            headers={"Content-Disposition": f"attachment; filename=execution_{execution_id}_report.pdf"}
        )

    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"PDF generation failed for execution {execution_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")
    finally:
        if conn:
            await db.release_db_connection(conn)
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.unlink(temp_pdf_path)
            except:
                pass
