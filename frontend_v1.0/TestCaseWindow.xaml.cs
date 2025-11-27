using System;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Windows;
using JPMCGenAI_v1._0.Services;

namespace JPMCGenAI_v1._0
{
    public partial class TestCaseDetailWindow : Window
    {
        private readonly ApiClient _api = new ApiClient();
        private string _originalTestCaseId = "";
        private string _projectId = "";

        public TestCaseDetailWindow(string testCaseId)
        {
            InitializeComponent();
            _api.SetBearer(Session.Token);
            LoadTestCase(testCaseId);
        }

        private async void LoadTestCase(string testCaseId)
        {
            try
            {
                var resp = await _api.GetAsync($"testcases/details?testcaseids={testCaseId}");
                resp.EnsureSuccessStatusCode();

                var json = await resp.Content.ReadAsStringAsync();
                var details = JsonSerializer.Deserialize<TestCaseDetails>(json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                var scenario = details?.Scenarios?.FirstOrDefault();
                if (scenario == null)
                {
                    MessageBox.Show("No scenario data found.");
                    return;
                }

                _originalTestCaseId = scenario.ScenarioId;
                _projectId = details.ProjectId;

                TitleLbl.Text = $"Editing {_originalTestCaseId}";

                TcIdInput.Text = scenario.ScenarioId;
                DescInput.Text = scenario.Description ?? "";
                PreTestIdInput.Text = scenario.PreTestId ?? "";
                PrereqInput.Text = scenario.Prerequisites?.FirstOrDefault()?.Description ?? "";
                TagsInput.Text = string.Join(",", scenario.Tags ?? Array.Empty<string>());

                var formattedSteps = scenario.Steps
                    .Select(s => new
                    {
                        Index = s.Index,
                        Description = s.Description,
                        TestDataText = s.TestDataText
                    })
                    .ToList();

                StepsDataGrid.ItemsSource = formattedSteps;
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error loading test case: " + ex.Message);
            }
        }

        private async void SaveChanges_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                string newTcId = TcIdInput.Text.Trim();

                // CHECK IF TESTCASE ID EXISTS IN SAME PROJECT
                var checkResp = await _api.GetAsync(
                    $"testcases/check-exists?testcaseid={newTcId}&projectid={_projectId}");

                var checkJson = await checkResp.Content.ReadAsStringAsync();
                var exists = JsonDocument.Parse(checkJson).RootElement.GetProperty("exists").GetBoolean();

                if (exists && newTcId != _originalTestCaseId)
                {
                    MessageBox.Show("Test Case ID already exists. Please choose another ID.",
                                    "Duplicate ID",
                                    MessageBoxButton.OK,
                                    MessageBoxImage.Warning);
                    return;
                }

                var payload = new
                {
                    old_testcaseid = _originalTestCaseId,
                    testcaseid = newTcId,
                    testdesc = DescInput.Text.Trim(),
                    pretestid = PreTestIdInput.Text.Trim(),
                    prereq = PrereqInput.Text.Trim(),
                    tag = TagsInput.Text.Trim(),
                    projectid = _projectId
                };

                var content = new StringContent(JsonSerializer.Serialize(payload),
                                                Encoding.UTF8,
                                                "application/json");

                var resp = await _api.PostAsync("testcases/update-detail", content);
                resp.EnsureSuccessStatusCode();

                MessageBox.Show("Test case updated successfully!",
                                "Success",
                                MessageBoxButton.OK,
                                MessageBoxImage.Information);

                LoadTestCase(newTcId);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error saving: " + ex.Message);
            }
        }
    }
}
