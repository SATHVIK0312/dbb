@router.get("/execution/{execution_id}/pdf")
async def get_execution_pdf(
        execution_id: str,
        current_user: dict = Depends(get_current_any_user)
):
    """
    Generate and download PDF for a specific execution record
    Fetches execution details and creates a formatted PDF with all information
    """
    conn = None
    temp_pdf_path = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Fetch execution record
        execution = await conn.fetchrow(
            """
            SELECT exeid, testcaseid, scripttype, datestamp, exetime, message, output, status
            FROM execution
            WHERE exeid = $1
            """,
            execution_id
        )

        if not execution:
            raise HTTPException(status_code=404, detail="Execution record not found")

        # Verify user access to this execution's test case
        testcase = await conn.fetchrow(
            "SELECT projectid FROM testcase WHERE testcaseid = $1",
            execution["testcaseid"]
        )

        if not testcase:
            raise HTTPException(status_code=404, detail="Test case not found")

        access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = $1 AND projectid && $2",
            userid,
            testcase["projectid"]
        )
        if not access:
            raise HTTPException(status_code=403, detail="You are not authorized to view this execution")

        # Get test case details
        test_case = await conn.fetchrow(
            "SELECT testdesc FROM testcase WHERE testcaseid = $1",
            execution["testcaseid"]
        )

        # Create PDF
        temp_pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
        doc = SimpleDocTemplate(
            temp_pdf_path,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=12,
            alignment=1  # Center
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#374151'),
            spaceAfter=8,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        )
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4b5563'),
            fontName='Helvetica-Bold'
        )
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1f2937'),
            alignment=0
        )

        # Build PDF content
        content = []

        # Title
        content.append(Paragraph("Test Execution Report", title_style))
        content.append(Spacer(1, 0.2 * inch))

        # Execution Summary Section
        content.append(Paragraph("Execution Summary", heading_style))

        summary_data = [
            [
                Paragraph("<b>Execution ID:</b>", label_style),
                Paragraph(str(execution["exeid"]), value_style)
            ],
            [
                Paragraph("<b>Test Case ID:</b>", label_style),
                Paragraph(str(execution["testcaseid"]), value_style)
            ],
            [
                Paragraph("<b>Test Case Description:</b>", label_style),
                Paragraph(str(test_case["testdesc"] if test_case else "N/A"), value_style)
            ],
            [
                Paragraph("<b>Script Type:</b>", label_style),
                Paragraph(str(execution["scripttype"]), value_style)
            ],
            [
                Paragraph("<b>Execution Date:</b>", label_style),
                Paragraph(str(execution["datestamp"]), value_style)
            ],
            [
                Paragraph("<b>Execution Time:</b>", label_style),
                Paragraph(str(execution["exetime"]), value_style)
            ],
            [
                Paragraph("<b>Status:</b>", label_style),
                Paragraph(
                    f"<font color='{_get_status_color(execution['status'])}' face='Helvetica-Bold'>{execution['status']}</font>",
                    value_style
                )
            ]
        ]

        summary_table = Table(summary_data, colWidths=[2.5 * inch, 3.5 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
        ]))
        content.append(summary_table)
        content.append(Spacer(1, 0.3 * inch))

        # Execution Message Section
        content.append(Paragraph("Execution Message", heading_style))
        message_text = execution["message"] or "No message provided"
        content.append(Paragraph(message_text, value_style))
        content.append(Spacer(1, 0.3 * inch))

        # Execution Output Section
        content.append(Paragraph("Execution Output", heading_style))

        output_text = execution["output"] or "No output captured"
        # Limit output length to prevent huge PDFs
        if len(output_text) > 5000:
            output_text = output_text[:5000] + "\n\n... (output truncated for PDF) ..."

        # Create scrollable output box
        output_lines = output_text.split('\n')
        for line in output_lines[:200]:  # Limit to 200 lines
            content.append(Paragraph(line if line.strip() else "&nbsp;", ParagraphStyle(
                'OutputLine',
                parent=styles['Normal'],
                fontSize=8,
                fontName='Courier',
                textColor=colors.HexColor('#374151'),
                spaceAfter=2
            )))

        # Build PDF
        doc.build(content)

        # Return PDF as download
        return FileResponse(
            temp_pdf_path,
            media_type="application/pdf",
            filename=f"execution_{execution_id}.pdf",
            headers={"Content-Disposition": "attachment; filename=execution_" + execution_id + ".pdf"}
        )

    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"PDF generation failed for execution {execution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    finally:
        if conn:
            await conn.close()
