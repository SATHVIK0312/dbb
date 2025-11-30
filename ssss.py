@router.post("/commit-staged-upload", response_model=models.CommitUploadResponse)
async def commit_staged_upload(
        request: models.CommitUploadData,
        current_user: dict = Depends(get_current_any_user)
):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # User allowed projects
        user_proj = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1",
            userid
        )
        if not user_proj:
            raise HTTPException(status_code=403, detail="User not assigned to any project")

        allowed = user_proj["projectid"]
        if isinstance(allowed, str):
            allowed = {allowed}
        else:
            allowed = set(allowed)

        selected_project = request.projectid
        if selected_project not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"You do not have access to project {selected_project}"
            )

        commit_count = 0

        for tc in request.testcases:
            tc_id = tc.get("testcaseid") or None
            if not tc_id:
                continue

            # Check duplicate
            existing = await conn.fetchrow(
                "SELECT testcaseid FROM testcase WHERE testcaseid = $1 AND $2 = ANY(projectid)",
                tc_id, selected_project
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Test case ID {tc_id} already exists in project {selected_project}"
                )

            tags = tc.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]

            # Insert testcase
            await conn.execute(
                """
                INSERT INTO testcase
                  (testcaseid, testdesc, pretestid, prereq, tag, projectid)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                tc_id,
                tc.get("testdesc", ""),
                tc.get("pretestid") or None,
                tc.get("prereq") or None,
                tags,
                [selected_project]
            )

            # Insert steps
            # Extract correct step text and args from structured objects
            steps_data = tc.get("steps", [])

            # Build PURIFIED arrays for Postgres
            step_texts = []
            step_args = []

            for s in steps_data:
                step_texts.append(s.get("step", "") or "")
                step_args.append(s.get("steparg", "") or "")

            await conn.execute(
                """
                INSERT INTO teststep (testcaseid, steps, args, stepnum)
                VALUES ($1, $2, $3, $4)
                """,
                tc_id,
                step_texts,  # VARCHAR[]
                step_args,  # VARCHAR[]
                len(step_texts)  # INTEGER
            )

            commit_count += 1

        return {
            "message": f"Upload committed successfully ({commit_count} test cases)",
            "testcases_committed": commit_count
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Commit failed: {str(e)}")
    finally:
        if conn:
            await conn.close()
