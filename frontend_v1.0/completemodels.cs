//using OfficeOpenXml;
//using System.Collections;
//using System.Collections.Generic;
//using System.IO;
//using System.Text.Json.Serialization;

//namespace jpmc_genai
//{
//    // ──────────────────────────────────────────────────────────────
//    // AUTH, PROJECT, USER MODELS
//    // ──────────────────────────────────────────────────────────────
//    public class LoginCreate
//    {
//        public string username { get; set; }
//        public string password { get; set; }
//    }

//    public class LoginResponse
//    {
//        public string userid { get; set; }
//        public string role { get; set; }
//        public string token { get; set; }
//        public List<Project> projects { get; set; }
//    }

//    public class Project
//    {
//        public string projectid { get; set; }
//        public string title { get; set; }
//        public string startdate { get; set; }
//        public string projecttype { get; set; }
//        public string description { get; set; }
//    }

//    public class RegisterCreate
//    {
//        public string name { get; set; }
//        public string mail { get; set; }
//        public string password { get; set; }
//        public string role { get; set; }
//    }

//    // ──────────────────────────────────────────────────────────────
//    // TEST CASE CORE MODELS
//    // ──────────────────────────────────────────────────────────────
//    public class TestCase
//    {
//        public string testcaseid { get; set; }
//        public string testdesc { get; set; }
//        public string pretestid { get; set; }
//        public string prereq { get; set; }
//        public List<string> tag { get; set; }
//        public List<string> projectid { get; set; }
//    }

//    public class TestCaseSteps
//    {
//        public string testcaseid { get; set; }
//        public List<string> steps { get; set; }
//        public List<string> args { get; set; }
//        public int stepnum { get; set; }
//    }

//    public class TestPlan
//    {
//        public string current_testid { get; set; }
//        public Dictionary<string, Dictionary<string, string>> pretestid_steps { get; set; }
//        public Dictionary<string, string> current_bdd_steps { get; set; }
//        public Dictionary<string, string> pretestid_scripts { get; set; }
//    }

//    public class ExecutionLog
//    {
//        public string exeid { get; set; }
//        public string testcaseid { get; set; }
//        public string scripttype { get; set; }
//        public string datestamp { get; set; }
//        public string exetime { get; set; }
//        public string message { get; set; }
//        public string output { get; set; }
//        public string status { get; set; }
//    }

//    // ──────────────────────────────────────────────────────────────
//    // STEP MODELS
//    // ──────────────────────────────────────────────────────────────
//    public class TestStepItem
//    {
//        public TestStepItem() { }
//        public TestStepItem(int stepNumber, string description, string action)
//        {
//            StepNumber = stepNumber;
//            Description = description;
//            Action = action;
//        }

//        public int StepNumber { get; set; }
//        public string Description { get; set; }
//        public string Action { get; set; }
//    }

//    public class StepResponse
//    {
//        public List<string> steps { get; set; } = new();
//        public List<string> args { get; set; } = new();
//        public int stepnum { get; set; }
//    }

//    public class TestCaseWithSteps
//    {
//        public string testcaseid { get; set; }
//        public string testdesc { get; set; }
//        public string pretestid { get; set; }
//        public string prereq { get; set; }
//        public List<string> tag { get; set; }
//        public List<string> projectid { get; set; }
//        public StepResponse steps { get; set; }
//    }

//    // ──────────────────────────────────────────────────────────────
//    // EXCEL UPLOAD / STAGING MODELS
//    // ──────────────────────────────────────────────────────────────
//    public class ExcelUploadTestCase
//    {
//        public string testcase_id { get; set; }
//        public string test_case_description { get; set; }
//        public string pre_requisite_test_id { get; set; }
//        public string pre_requisite_description { get; set; }
//        public string tags { get; set; }
//        public string test_steps { get; set; }
//        public string arguments { get; set; }
//        public string project_id { get; set; }
//    }

//    public class StagedTestCase
//    {
//        public string testcaseid { get; set; }
//        public string testdesc { get; set; }
//        public string pretestid { get; set; }
//        public string prereq { get; set; }
//        public List<string> tags { get; set; }
//        public List<string> projectids { get; set; }
//        public List<Dictionary<string, object>> steps { get; set; }
//    }

//    public class StageUploadResponse
//    {
//        public string message { get; set; }
//        public int testcases_count { get; set; }
//        public List<StagedTestCase> staged_testcases { get; set; }
//    }

//    public class CommitUploadData
//    {
//        public string projectid { get; set; }
//        public List<Dictionary<string, object>> testcases { get; set; }
//    }

//// ──────────────────────────────────────────────────────────────
//// NORMALIZATION / PREVIEW MODELS
//// ──────────────────────────────────────────────────────────────
//public class NormalizedStep
//{
//    public int Index { get; set; }
//    public string Step { get; set; } = "";
//    public string TestDataText { get; set; } = "";
//    public Dictionary<string, object> TestData { get; set; } = new();
//}

//public class NormalizeResponse
//{
//    public string TestCaseId { get; set; } = "";
//    public List<NormalizedStep> Original_Steps { get; set; } = new();
//    public List<NormalizedStep> Normalized_Steps { get; set; } = new();
//    public string Message { get; set; } = "";
//}

//    // ──────────────────────────────────────────────────────────────
//    // TEST STEP INFO FOR EDIT WINDOW
//    // ──────────────────────────────────────────────────────────────
//    public class TestStepInfo
//    {
//        public string testcaseid { get; set; } = "";
//        public List<string> steps { get; set; } = new();
//        public List<string> args { get; set; } = new();
//        public int stepnum { get; set; }
//    }

//    public class EditableStep
//    {
//        public int Index { get; set; }
//        public string Step { get; set; } = "";
//        public string TestDataText { get; set; } = "";
//    }

//    // ──────────────────────────────────────────────────────────────
//    // TEST CASE DETAILS (SCENARIO + PREREQUISITES)
//    // ──────────────────────────────────────────────────────────────
//    public class Step
//    {
//        public int Index { get; set; }

//        [JsonPropertyName("Step")]
//        public string Description { get; set; } = "";

//        public string TestDataText { get; set; } = "";
//        public Dictionary<string, object>? TestData { get; set; }
//    }

//    public class Prerequisite
//    {
//        public string PrerequisiteID { get; set; }
//        public string Description { get; set; }
//    }

//    public class Scenario
//    {
//        public string ScenarioId { get; set; } = "";
//        public string Description { get; set; } = "";
//        public List<Prerequisite> Prerequisites { get; set; } = new();
//        public bool IsBdd { get; set; }
//        public string Status { get; set; } = "draft";
//        public List<Step> Steps { get; set; } = new();
//    }

//    public class TestCaseDetails
//    {
//        public List<Scenario> Scenarios { get; set; } = new();
//    }

//    // ──────────────────────────────────────────────────────────────
//    // PAGINATION
//    // ──────────────────────────────────────────────────────────────
//    public class PaginatedTestCaseResponse
//    {
//        public string testcaseid { get; set; }
//        public string testdesc { get; set; }
//        public string pretestid { get; set; }
//        public string prereq { get; set; }
//        public List<string> tag { get; set; }
//        public List<string> projectid { get; set; }
//        public int steps_count { get; set; }
//    }

//    public class PaginatedTestCasesResponse
//    {
//        public int page { get; set; }
//        public int page_size { get; set; }
//        public int total_count { get; set; }
//        public int total_pages { get; set; }
//        public List<PaginatedTestCaseResponse> testcases { get; set; }
//        public string message { get; set; }
//    }

//    //public class PaginatedTestCaseResponse
//    //{
//    //    public string testcaseid { get; set; }
//    //    public string testdesc { get; set; }
//    //    public string pretestid { get; set; }
//    //    public string prereq { get; set; }
//    //    public List<string> tag { get; set; }
//    //    public List<string> projectid { get; set; }
//    //    public int steps_count { get; set; }
//    //}

//    //public class PaginatedTestCasesResponse
//    //{
//    //    public int page { get; set; }
//    //    public int page_size { get; set; }
//    //    public int total_count { get; set; }
//    //    public int total_pages { get; set; }
//    //    public List<PaginatedTestCaseResponse> testcases { get; set; }
//    //    public string message { get; set; }
//    //}

//    //public class CommitUploadData
//    //{
//    //    public string projectid { get; set; }
//    //    public List<Dictionary<string, object>> testcases { get; set; }
//    //}

//    // ──────────────────────────────────────────────────────────────
//    // MISSING CLASSES – ADD THESE AT THE END OF THE FILE
//    // ──────────────────────────────────────────────────────────────

//    public class GroupedTestCase
//    {
//        public string TestCaseId { get; set; } = "";
//        public string Description { get; set; } = "";
//        public string PreReqId { get; set; } = "";
//        public string PreReqDesc { get; set; } = "";
//        public List<string> Tags { get; set; } = new();
//        public List<TestStep> Steps { get; set; } = new();
//    }
//    public class NormalizeApiResponse
//    {
//        [JsonPropertyName("testcaseid")]
//        public string TestCaseId { get; set; } = "";

//        [JsonPropertyName("original")]
//        public List<NormalizedStep> Original { get; set; } = new();

//        [JsonPropertyName("normalized")]
//        public List<NormalizedStep> Normalized { get; set; } = new();

//        [JsonPropertyName("message")]
//        public string Message { get; set; } = "";
//    }

//    public class TestStep
//    {
//        public string? Step { get; set; }
//        public string? Argument { get; set; }


//        // ──────────────────────────────────────────────────────────────
//        // EXCEL PARSER – ADD THIS METHOD (fixes ParseExcelWithGrouping error)
//        // ──────────────────────────────────────────────────────────────
//        private List<GroupedTestCase> ParseExcelWithGrouping(string filePath)
//        {
//            var testCases = new List<GroupedTestCase>();
//            var package = new ExcelPackage(new FileInfo(filePath));
//            var worksheet = package.Workbook.Worksheets[0];

//            GroupedTestCase? currentTc = null;

//            for (int row = 2; row <= worksheet.Dimension.End.Row; row++)
//            {
//                var idCell = worksheet.Cells[row, 1].Value?.ToString()?.Trim();
//                var descCell = worksheet.Cells[row, 2].Value?.ToString()?.Trim();
//                var stepCell = worksheet.Cells[row, 3].Value?.ToString()?.Trim();
//                var argCell = worksheet.Cells[row, 4].Value?.ToString()?.Trim();

//                if (string.IsNullOrEmpty(idCell))
//                {
//                    // Continuation row — add step to current test case
//                    if (currentTc != null && !string.IsNullOrEmpty(stepCell))
//                    {
//                        currentTc.Steps.Add(new TestStep { Step = stepCell, Argument = argCell });
//                    }
//                    continue;
//                }

//                // New test case
//                currentTc = new GroupedTestCase
//                {
//                    TestCaseId = idCell,
//                    Description = descCell ?? "",
//                    Steps = new List<TestStep>()
//                };

//                if (!string.IsNullOrEmpty(stepCell))
//                {
//                    currentTc.Steps.Add(new TestStep { Step = stepCell, Argument = argCell });
//                }

//                testCases.Add(currentTc);
//            }

//            package.Dispose();
//            return testCases;
//        }
//    }
//}

using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace jpmc_genai
{
    // ──────────────────────────────────────────────────────────────
    // AUTH & SESSION MODELS
    // ──────────────────────────────────────────────────────────────
    public class LoginCreate
    {
        public string username { get; set; } = "";
        public string password { get; set; } = "";
    }

    public class LoginResponse
    {
        public string userid { get; set; } = "";
        public string role { get; set; } = "";
        public string token { get; set; } = "";
        public List<Project> projects { get; set; } = new();
    }

    public class Project
    {
        public string projectid { get; set; } = "";
        public string title { get; set; } = "";
        public string startdate { get; set; } = "";
        public string projecttype { get; set; } = "";
        public string description { get; set; } = "";
    }

    public class RegisterCreate
    {
        public string name { get; set; } = "";
        public string mail { get; set; } = "";
        public string password { get; set; } = "";
        public string role { get; set; } = "";
    }

    // ──────────────────────────────────────────────────────────────
    // TEST CASE CORE MODELS
    // ──────────────────────────────────────────────────────────────
    public class TestCase
    {
        public string testcaseid { get; set; } = "";
        public string testdesc { get; set; } = "";
        public string pretestid { get; set; } = "";
        public string prereq { get; set; } = "";
        public List<string> tag { get; set; } = new();
        public List<string> projectid { get; set; } = new();
    }

    public class TestCaseSteps
    {
        public string testcaseid { get; set; } = "";
        public List<string> steps { get; set; } = new();
        public List<string> args { get; set; } = new();
        public int stepnum { get; set; }
    }

    // ──────────────────────────────────────────────────────────────
    // EXCEL UPLOAD & STAGING MODELS
    // ──────────────────────────────────────────────────────────────

    public class TestPlan
    {
        public string current_testid { get; set; }
        public Dictionary<string, Dictionary<string, string>> pretestid_steps { get; set; }
        public Dictionary<string, string> current_bdd_steps { get; set; }
        public Dictionary<string, string> pretestid_scripts { get; set; }
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

    public class TestStep
    {
        public string Step { get; set; } = "";
        public string Argument { get; set; } = "";
    }

    public class CommitUploadData
    {
        public string projectid { get; set; } = "";
        public List<Dictionary<string, object>> testcases { get; set; } = new();
    }

    // ──────────────────────────────────────────────────────────────
    // NORMALIZATION / PREVIEW MODELS
    // ──────────────────────────────────────────────────────────────
public class NormalizedStep
    {
        public int Index { get; set; }
        public string Step { get; set; } = "";
        public string TestDataText { get; set; } = "";
        public Dictionary<string, object> TestData { get; set; } = new();
    }

    public class NormalizeResponse
    {
        public string TestCaseId { get; set; } = "";
        public List<NormalizedStep> Original_Steps { get; set; } = new();
        public List<NormalizedStep> Normalized_Steps { get; set; } = new();
        public string Message { get; set; } = "";
    }

    /// <summary>
    /// This model PERFECTLY matches the JSON returned by /normalize-uploaded
    /// Uses [JsonPropertyName] to map snake_case from Python → C#
    /// </summary>
    public class NormalizeApiResponse
    {
        [JsonPropertyName("testcaseid")]
        public string TestCaseId { get; set; } = "";

        [JsonPropertyName("original_steps")]
        public List<NormalizedStep> OriginalSteps { get; set; } = new();

        [JsonPropertyName("normalized_steps")]
        public List<NormalizedStep> NormalizedSteps { get; set; } = new();

        [JsonPropertyName("message")]
        public string Message { get; set; } = "";
    }

    // Backward compatibility


    // ──────────────────────────────────────────────────────────────
    // TEST CASE DETAILS (View/Edit Window)
    // ──────────────────────────────────────────────────────────────
    public class Step
    {
        public int Index { get; set; }

        [JsonPropertyName("Step")]
        public string Description { get; set; } = "";

        public string TestDataText { get; set; } = "";
        public Dictionary<string, object>? TestData { get; set; }
    }

    public class Prerequisite
    {
        public string PrerequisiteID { get; set; } = "";
        public string Description { get; set; } = "";
    }

    public class Scenario
    {
        public string ScenarioId { get; set; } = "";
        public string Description { get; set; } = "";
        public List<Prerequisite> Prerequisites { get; set; } = new();
        public bool IsBdd { get; set; } = true;
        public string Status { get; set; } = "draft";
        public List<Step> Steps { get; set; } = new();
    }

    public class TestCaseDetails
    {
        public List<Scenario> Scenarios { get; set; } = new();
    }

    // ──────────────────────────────────────────────────────────────
    // EDIT WINDOW MODELS
    // ──────────────────────────────────────────────────────────────
    public class TestStepInfo
    {
        public string testcaseid { get; set; } = "";
        public List<string> steps { get; set; } = new();
        public List<string> args { get; set; } = new();
        public int stepnum { get; set; }
    }

    public class EditableStep
    {
        public int Index { get; set; }
        public string Step { get; set; } = "";
        public string TestDataText { get; set; } = "";
    }

    // ──────────────────────────────────────────────────────────────
    // PAGINATION RESPONSE
    // ──────────────────────────────────────────────────────────────
    public class PaginatedTestCaseResponse
    {
        public string testcaseid { get; set; } = "";
        public string testdesc { get; set; } = "";
        public string pretestid { get; set; } = "";
        public string prereq { get; set; } = "";
        public List<string> tag { get; set; } = new();
        public List<string> projectid { get; set; } = new();
        public int steps_count { get; set; }
    }

    public class PaginatedTestCasesResponse
    {
        public int page { get; set; }
        public int page_size { get; set; }
        public int total_count { get; set; }
        public int total_pages { get; set; }
        public List<PaginatedTestCaseResponse> testcases { get; set; } = new();
        public string message { get; set; } = "";
    }

    // ──────────────────────────────────────────────────────────────
    // EXECUTION LOG (if needed)
    // ──────────────────────────────────────────────────────────────
    public class ExecutionLog
    {
        public string exeid { get; set; } = "";
        public string testcaseid { get; set; } = "";
        public string scripttype { get; set; } = "";
        public string datestamp { get; set; } = "";
        public string exetime { get; set; } = "";
        public string message { get; set; } = "";
        public string output { get; set; } = "";
        public string status { get; set; } = "";
    }
}

