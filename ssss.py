private List<GroupedTestCase> ParseExcelWithGrouping(string path)
{
    var result = new List<GroupedTestCase>();
    GroupedTestCase current = null;

    using var package = new ExcelPackage(new FileInfo(path));
    var ws = package.Workbook.Worksheets[0];

    // Validate header: StepNo must be at column 6
    var headerStepNo = ws.Cells[1, 6].GetValue<string>()?.Trim();
    if (string.IsNullOrWhiteSpace(headerStepNo) ||
        !headerStepNo.Equals("StepNo", StringComparison.OrdinalIgnoreCase))
        throw new Exception("Excel must contain 'StepNo' column at column 6 (before Step).");

    for (int row = 2; row <= ws.Dimension.End.Row; row++)
    {
        var rawId = ws.Cells[row, 1].GetValue<string>()?.Trim();
        string id = string.IsNullOrWhiteSpace(rawId) ? current?.TestCaseId : rawId;

        var desc = ws.Cells[row, 2].GetValue<string>()?.Trim() ?? "";
        var preReqId = ws.Cells[row, 3].GetValue<string>()?.Trim();
        var preReqDesc = ws.Cells[row, 4].GetValue<string>()?.Trim();
        var tagsRaw = ws.Cells[row, 5].GetValue<string>()?.Trim() ?? "";
        var stepNoCell = ws.Cells[row, 6].GetValue<string>()?.Trim();
        var stepText = ws.Cells[row, 7].GetValue<string>()?.Trim();
        var argText = ws.Cells[row, 8].GetValue<string>()?.Trim();

        bool hasId = !string.IsNullOrWhiteSpace(rawId);
        bool hasStepNo = !string.IsNullOrWhiteSpace(stepNoCell);
        bool hasStepDesc = !string.IsNullOrWhiteSpace(stepText);

        // ---------------------------------------------------------
        // RULE 1 — Valid Scenario Start
        // ---------------------------------------------------------
        if (hasId)
        {
            if (string.IsNullOrWhiteSpace(desc))
                throw new Exception($"Row {row}: Scenario Name cannot be empty when Scenario ID is present.");

            if (!hasStepNo || stepNoCell != "1")
                throw new Exception($"Row {row}: Scenario start must have StepNo = 1.");

            // Prerequisite consistency applies here (Rule 4)
            if (!string.IsNullOrWhiteSpace(preReqId) && string.IsNullOrWhiteSpace(preReqDesc))
                throw new Exception($"Row {row}: Prerequisite ID is filled but Description is missing.");

            if (!string.IsNullOrWhiteSpace(preReqDesc) && string.IsNullOrWhiteSpace(preReqId))
                throw new Exception($"Row {row}: Prerequisite Description is filled but Prerequisite ID is missing.");

            // Start a new scenario
            if (current != null)
                result.Add(current);

            current = new GroupedTestCase
            {
                TestCaseId = id,
                Description = desc,
                PreReqId = preReqId ?? "",
                PreReqDesc = preReqDesc ?? "",
                Tags = tagsRaw.Split(',', StringSplitOptions.RemoveEmptyEntries)
                              .Select(t => t.Trim()).ToList(),
                Steps = new List<TestStep>()
            };
        }
        else
        {
            // ---------------------------------------------------------
            // RULE 2 — Continuation row format
            // ---------------------------------------------------------
            if (current == null)
                continue; // skip blank rows before first scenario

            if (!hasStepNo)
                throw new Exception($"Row {row}: StepNo must be present for continuation rows.");

            if (!int.TryParse(stepNoCell, out int parsedStep))
                throw new Exception($"Row {row}: Invalid StepNo '{stepNoCell}'.");

            if (parsedStep <= 1)
                throw new Exception($"Row {row}: Continuation rows must have StepNo > 1.");

            if (!hasStepDesc)
                throw new Exception($"Row {row}: Step description is required for continuation rows.");
        }

        // ---------------------------------------------------------
        // RULE 3 — Required Step Description
        // ---------------------------------------------------------
        if (hasStepNo && !hasStepDesc)
            throw new Exception($"Row {row}: StepNo is provided but Step description is missing.");

        // ---------------------------------------------------------
        // RULE 4 — Prerequisite consistency only allowed on Step 1
        // ---------------------------------------------------------
        if (hasStepNo && stepNoCell != "1")
        {
            if (!string.IsNullOrWhiteSpace(preReqId) || !string.IsNullOrWhiteSpace(preReqDesc))
                throw new Exception($"Row {row}: Prerequisite fields allowed only on StepNo = 1.");
        }

        // ---------------------------------------------------------
        // Add step to scenario
        // ---------------------------------------------------------
        if (hasStepNo)
        {
            if (!int.TryParse(stepNoCell, out int stepNo))
                throw new Exception($"Row {row}: StepNo must be numeric.");

            current.Steps.Add(new TestStep
            {
                StepNo = stepNo,
                Step = stepText ?? "",
                Argument = argText ?? ""
            });
        }
    }

    if (current != null)
        result.Add(current);

    return result;
}
