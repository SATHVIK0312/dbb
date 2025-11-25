using JPMCGenAI_v1._0.Services;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;

namespace JPMCGenAI_v1._0
{
    public partial class TestCaseDetailsDialog : Window
    {
        private readonly string _testCaseId;
        private readonly ApiClient _api = new ApiClient();

        private readonly ObservableCollection<TestStepRow> _steps = new();

        public TestCaseDetailsDialog(string testCaseId)
        {
            InitializeComponent();

            _testCaseId = testCaseId;

            TestStepsDataGrid.ItemsSource = _steps;

            MakeReadOnly();

            _ = LoadTestCaseAsync();
        }

        // -------------------------------------------------------
        // MAKE EVERYTHING READ-ONLY
        // -------------------------------------------------------
        private void MakeReadOnly()
        {
            TestCaseIdTextBox.IsReadOnly = true;
            TestDescriptionTextBox.IsReadOnly = true;
            TagsTextBox.IsReadOnly = true;
            PrerequisitesTextBox.IsReadOnly = true;

            TestStepsDataGrid.IsReadOnly = true;
        }

        // -------------------------------------------------------
        // MODELS
        // -------------------------------------------------------
        public class TestStepRow
        {
            public int StepNumber { get; set; }
            public string Description { get; set; }
            public string Action { get; set; }
        }

        public class TestCaseDetailsResponse
        {
            public List<TestScenario> Scenarios { get; set; }
        }

        public class TestScenario
        {
            public string ScenarioId { get; set; }
            public string Description { get; set; }

            public List<PrereqObject> Prerequisites { get; set; }

            public List<TestStepDetail> Steps { get; set; }
        }

        public class PrereqObject
        {
            public string PrerequisiteID { get; set; }
            public string Description { get; set; }
        }

        public class TestStepDetail
        {
            public int Index { get; set; }
            public string Step { get; set; }
            public string TestDataText { get; set; }
        }

        // -------------------------------------------------------
        // LOAD TEST CASE DETAILS (supports prereq objects)
        // -------------------------------------------------------
        private async Task LoadTestCaseAsync()
        {
            try
            {
                _api.SetBearer(Session.Token);

                var response = await _api.GetAsync($"testcases/details?testcaseids={_testCaseId}");

                if (!response.IsSuccessStatusCode)
                {
                    MessageBox.Show($"Failed to load test case: {response.StatusCode}");
                    return;
                }

                string json = await response.Content.ReadAsStringAsync();
                TestStepsJsonTextBox.Text = json;

                var data = JsonSerializer.Deserialize<TestCaseDetailsResponse>(json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                if (data?.Scenarios == null || data.Scenarios.Count == 0)
                {
                    MessageBox.Show("Invalid response from API");
                    return;
                }

                var scenario = data.Scenarios[0];

                // Fill header
                TestCaseIdTextBox.Text = scenario.ScenarioId;
                TestDescriptionTextBox.Text = scenario.Description ?? "";
                TagsTextBox.Text = "";

                // Convert prereq objects → readable text
                if (scenario.Prerequisites != null && scenario.Prerequisites.Count > 0)
                {
                    PrerequisitesTextBox.Text =
                        string.Join(", ",
                            scenario.Prerequisites.ConvertAll(
                                p => $"{p.PrerequisiteID}: {p.Description}"
                            ));
                }
                else
                {
                    PrerequisitesTextBox.Text = "None";
                }

                // Fill steps
                _steps.Clear();

                foreach (var s in scenario.Steps)
                {
                    _steps.Add(new TestStepRow
                    {
                        StepNumber = s.Index,
                        Description = s.Step,
                        Action = s.TestDataText
                    });
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error loading test case details: {ex.Message}");
            }
        }

        // -------------------------------------------------------
        // CLOSE BUTTON ONLY
        // -------------------------------------------------------
        private void CancelButton_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
