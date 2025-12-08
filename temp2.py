






import os
import tempfile
from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import utils


# ✅ STATUS COLOR HELPER
def _get_status_color(status: str) -> str:
    colors_map = {
        "SUCCESS": "#10b981",
        "COMPLETED": "#3b82f6",
        "FAILED": "#ef4444",
        "ERROR": "#f97316"
    }
    return colors_map.get(status, "#6b7280")


# ✅ FINAL WORKING ENDPOINT
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

        # ✅ FIX 1: Correct SQLite Binding (TUPLE REQUIRED)
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

        execution = execution[0]  # ✅ list → row

        # ✅ FIX 2: Fetch Project ID
        testcase = await conn.execute_fetchall(
            "SELECT projectid FROM testcase WHERE testcaseid = ?",
            (execution["testcaseid"],)
        )

        if not testcase:
            raise HTTPException(status_code=404, detail="Test case not found")

        testcase = testcase[0]

        # ✅ FIX 3: Project Access Validation
        access = await conn.execute_fetchall(
            "SELECT 1 FROM projectuser WHERE userid = ? AND projectid = ?",
            (userid, testcase["projectid"])
        )

        if not access:
            raise HTTPException(status_code=403, detail="You are not authorized to view this execution")

        # ✅ FIX 4: Fetch Test Description
        test_case = await conn.execute_fetchall(
            "SELECT testdesc FROM testcase WHERE testcaseid = ?",
            (execution["testcaseid"],)
        )

        test_desc = test_case[0]["testdesc"] if test_case else "N/A"

        # ✅ CREATE TEMP PDF FILE
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

        # ✅ TITLE
        content.append(Paragraph("Test Execution Report", title_style))
        content.append(Spacer(1, 0.2 * inch))

        # ✅ EXECUTION SUMMARY
        content.append(Paragraph("Execution Summary", heading_style))

        summary_data = [
            [Paragraph("Execution ID", label_style), Paragraph(str(execution["exeid"]), value_style)],
            [Paragraph("Test Case ID", label_style), Paragraph(str(execution["testcaseid"]), value_style)],
            [Paragraph("Test Case Description", label_style), Paragraph(test_desc, value_style)],
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

        # ✅ EXECUTION MESSAGE
        content.append(Paragraph("Execution Message", heading_style))
        message = execution["message"] or "No message available"
        content.append(Paragraph(message, value_style))
        content.append(Spacer(1, 0.3 * inch))

        # ✅ EXECUTION OUTPUT
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

        # ✅ BUILD PDF
        doc.build(content)

        # ✅ RETURN FILE
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
