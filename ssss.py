#region Excel Parser & Models
private List<GroupedTestCase> ParseExcelWithGrouping(string path)
{
    var result = new List<GroupedTestCase>();
    GroupedTestCase current = null;

    using var package = new ExcelPackage(new FileInfo(path));
    var ws = package.Workbook.Worksheets[0];

    // Validate header: StepNo must be at column 6 (Option A)
    var headerStepNo = ws.Cells[1, 6].GetValue<string>()?.Trim();
    if (string.IsNullOrWhiteSpace(headerStepNo) || !headerStepNo.Equals("StepNo", StringComparison.OrdinalIgnoreCase))
        throw new Exception("Excel must contain 'StepNo' column at column 6 (before Step).");

    for (int row = 2; row <= ws.Dimension.End.Row; row++)
    {
        var rawId = ws.Cells[row, 1].GetValue<string>()?.Trim();
        string id = string.IsNullOrWhiteSpace(rawId) ? current?.TestCaseId : rawId;

        // SKIP empty rows until first real test case appears
        if (string.IsNullOrWhiteSpace(rawId) && current == null)
            continue;

        var desc = ws.Cells[row, 2].GetValue<string>()?.Trim() ?? "";

        // ---------------------------------------------------
        // ⭐ RULE ADDED: Test Case Description must not be empty
        // ---------------------------------------------------
        if (!string.IsNullOrWhiteSpace(id) && string.IsNullOrWhiteSpace(desc))
        {
            throw new Exception($"Test Case Description cannot be empty for TestCaseId '{id}' at row {row}.");
        }

        // Column mapping per Option A:
        // col 6 -> StepNo
        // col 7 -> Step
        // col 8 -> Argument
        var stepNoCell = ws.Cells[row, 6].GetValue<string>()?.Trim();
        var stepText = ws.Cells[row, 7].GetValue<string>()?.Trim();
        var argText = ws.Cells[row, 8].GetValue<string>()?.Trim();

        if (current == null || current.TestCaseId != id)
        {
            if (current != null)
                result.Add(current);

            current = new GroupedTestCase
            {
                TestCaseId = id,
                Description = desc,
                PreReqId = ws.Cells[row, 3].GetValue<string>() ?? "",
                PreReqDesc = ws.Cells[row, 4].GetValue<string>() ?? "",
                Tags = (ws.Cells[row, 5].GetValue<string>() ?? "")
                    .Split(',', StringSplitOptions.RemoveEmptyEntries)
                    .Select(t => t.Trim()).ToList(),
                Steps = new List<TestStep>()
            };
        }

        // If row contains step data, StepNo must be valid
        if (!string.IsNullOrWhiteSpace(stepText) || !string.IsNullOrWhiteSpace(argText))
        {
            if (string.IsNullOrWhiteSpace(stepNoCell))
                throw new Exception($"Missing StepNo at row {row}. Please provide StepNo in column 6.");

            if (!int.TryParse(stepNoCell, out int stepNo))
                throw new Exception($"Invalid StepNo '{stepNoCell}' at row {row}. StepNo must be a number.");

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

public class GroupedTestCase
{
    public string TestCaseId { get; set; } = "";
    public string Description { get; set; } = "";
    public string PreReqId { get; set; } = "";
    public string PreReqDesc { get; set; } = "";
    public List<string> Tags { get; set; } = new();
    public List<TestStep> Steps { get; set; } = new();
}
#endregion
