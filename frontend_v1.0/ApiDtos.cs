namespace JPMCGenAI_v1._0
{
    // DTO used ONLY for deserialization of backend JSON
    public class StepDto
    {
        public int Index { get; set; }
        public string Step { get; set; } = "";
        public string TestDataText { get; set; } = "";
        public Dictionary<string, object>? TestData { get; set; }
    }

    public class PrerequisiteDto
    {
        public string PrerequisiteID { get; set; } = "";
        public string Description { get; set; } = "";
    }

    public class ScenarioDto
    {
        public string ScenarioId { get; set; } = "";
        public string Description { get; set; } = "";
        public List<StepDto> Steps { get; set; } = new();
        public List<PrerequisiteDto> Prerequisites { get; set; } = new();
        public string Status { get; set; } = "";
    }

    public class TestCaseDetailsDto
    {
        public List<ScenarioDto> Scenarios { get; set; } = new();
    }
}
