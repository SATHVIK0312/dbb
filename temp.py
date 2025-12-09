import os
import tempfile
import re  # ← ONLY NEW IMPORT
from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import utils

# STATUS COLOR HELPER
def _get_status_color(status: str) -> str:
    colors_map = {
        "SUCCESS": "#10b981",
        "COMPLETED": "#3b82f6",
        "FAILED": "#ef4444",
        "ERROR": "#f97316"
    }
    return colors_map.get(status, "#6b7280")

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
        if not execution_id:
            raise HTTPException(status_code=400, detail="Invalid execution ID")

        execution = await conn.execute_fetchall(
            """
            SELECT exeid, testcaseid, scripttype, datestamp, exetime, message, output, status
            FROM execution
            WHERE exeid = ?
            """,
            (str(execution_id).strip(),)
        )
        if not execution:
            raise HTTPException(status_code=404, detail="Execution record not found")
        execution = execution[0]

        # Project access check (kept from your original)
        testcase = await conn.execute_fetchall(
            "SELECT projectid FROM testcase WHERE testcaseid = ?",
            (execution["testcaseid"],)
        )
        if not testcase:
            raise HTTPException(status_code=404, detail="Test case not found")
        testcase = testcase[0]

        access = await conn.execute_fetchall(
            "SELECT 1 FROM projectuser WHERE userid = ? AND projectid = ?",
            (userid, testcase["projectid"])
        )
        if not access:
            raise HTTPException(status_code=403, detail="You are not authorized to view this execution")

        # EXTRACT SCRIPT PATH FROM message FIELD
        message_text = execution["message"] or ""
        script_path = None
        # Look for pattern like: Stored at: I:\some\path\file.py
        match = re.search(r'Stored at:\s*([A-Za-z]:\\[^\s"\'<>|]+)', message_text, re.IGNORECASE)
        if match:
            script_path = match.group(1).strip()

        # Read the actual script file if path found
        script_code = "No script path found in message."
        if script_path and os.path.isfile(script_path):
            try:
                with open(script_path, "r", encoding="utf-8") as f:
                    script_code = f.read()
                if len(script_code) > 10000:
                    script_code = script_code[:10000] + "\n\n... [CODE TRUNCATED] ..."
            except:
                script_code = "Failed to read script file from path."
        elif script_path:
            script_code = f"Script file not found on server:\n{script_path}"

        # CREATE TEMP PDF FILE
        temp_pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
        doc = SimpleDocTemplate(
            temp_pdf_path,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#1f2937"),
            alignment=1,
            spaceAfter=12
        )
        heading_style = ParagraphStyle(
            "Heading",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#374151"),
            spaceBefore=10,
            spaceAfter=6
        )
        label_style = ParagraphStyle(
            "Label",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#4b5563"),
            fontName="Helvetica-Bold"
        )
        value_style = ParagraphStyle(
            "Value",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#1f2937")
        )
        content = []

        # TITLE
        content.append(Paragraph("Test Execution Report", title_style))
        content.append(Spacer(1, 0.2 * inch))

        # EXECUTION SUMMARY (your original)
        content.append(Paragraph("Execution Summary", heading_style))
        summary_data = [
            [Paragraph("Execution ID", label_style), Paragraph(str(execution["exeid"]), value_style)],
            [Paragraph("Test Case ID", label_style), Paragraph(str(execution["testcaseid"]), value_style)],
            [Paragraph("Script Type", label_style), Paragraph(str(execution["scripttype"]), value_style)],
            [Paragraph("Execution Date", label_style), Paragraph(str(execution["datestamp"]), value_style)],
            [Paragraph("Execution Time", label_style), Paragraph(str(execution["exetime"]), value_style)],
            [
                Paragraph("Status", label_style),
                Paragraph(
                    f"<font color='{_get_status_color(execution['status'])}'><b>{execution['status']}</b></font>",
                    value_style,
                ),
            ],
        ]
        summary_table = Table(summary_data, colWidths=[2.5 * inch, 3.5 * inch])
        summary_table.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 1, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        content.append(summary_table)
        content.append(Spacer(1, 0.3 * inch))

        # EXECUTION MESSAGE (your original)
        content.append(Paragraph("Execution Message", heading_style))
        message = execution["message"] or "No message available"
        content.append(Paragraph(message, value_style))
        content.append(Spacer(1, 0.3 * inch))

        # EXECUTION OUTPUT (your original)
        content.append(Paragraph("Execution Output", heading_style))
        output_text = execution["output"] or "No output available"
        if len(output_text) > 5000:
            output_text = output_text[:5000] + "\n\n... Output Truncated ..."
        for line in output_text.splitlines()[:200]:
            content.append(
                Paragraph(
                    line if line.strip() else "&nbsp;",
                    ParagraphStyle(
                        "Output",
                        parent=styles["Normal"],
                        fontSize=8,
                        fontName="Courier",
                        textColor=colors.HexColor("#374151"),
                        spaceAfter=2,
                    ),
                )
            )

        # NEW: SCRIPT SOURCE CODE SECTION (only addition)
        content.append(Spacer(1, 0.4 * inch))
        content.append(Paragraph("Script Source Code", heading_style))
        for line in script_code.splitlines():
            safe_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if not safe_line.strip():
                safe_line = "&nbsp;"
            content.append(
                Paragraph(
                    safe_line,
                    ParagraphStyle(
                        "Code",
                        parent=styles["Normal"],
                        fontSize=8,
                        fontName="Courier",
                        textColor=colors.HexColor("#374151"),
                        spaceAfter=2,
                    ),
                )
            )

        # BUILD PDF
        doc.build(content)

        return FileResponse(
            temp_pdf_path,
            media_type="application/pdf",
            filename=f"execution_{execution_id}.pdf",
            headers={
                "Content-Disposition": f"attachment; filename=execution_{execution_id}.pdf"
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"PDF generation failed for execution {execution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    finally:
        if conn:
            await db.release_db_connection(conn)
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)
