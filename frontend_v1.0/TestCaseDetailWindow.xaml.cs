using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Windows;
using JPMCGenAI_v1._0.Services;

namespace JPMCGenAI_v1._0
{
    public partial class TestCaseDetailWindow : Window
    {
        private readonly ApiClient _api = new ApiClient();

        public TestCaseDetailWindow(string testCaseId)
        {
            InitializeComponent();
            _api.SetBearer(Session.Token);
            LoadTestCaseDetails(testCaseId);
        }

        private async void LoadTestCaseDetails(string testCaseId)
        {
            try
            {
                TitleLbl.Text = $"Loading {testCaseId}...";
                _api.SetBearer(Session.Token);

                //
                // 1) Fetch EVERYTHING from details endpoint (correct backend)
                //
                var resp = await _api.GetAsync($"testcases/details?testcaseids={testCaseId}");
                resp.EnsureSuccessStatusCode();

                var json = await resp.Content.ReadAsStringAsync();
                var details = JsonSerializer.Deserialize<TestCaseDetails>(json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                var scenario = details?.Scenarios?.FirstOrDefault();
                if (scenario == null)
                {
                    StepsDataGrid.ItemsSource = new[]
                    {
                new { Index = 0, Description = "No scenario found", TestDataText = "" }
            };
                    return;
                }

                //
                // 2) Metadata
                //
                TitleLbl.Text = $"{scenario.ScenarioId} – {scenario.Description}";
                TcIdText.Text = scenario.ScenarioId;
                DescText.Text = scenario.Description ?? "";

                TagsText.Text = scenario.Prerequisites?.Any() == true
                    ? string.Join(" • ", scenario.Prerequisites.Select(p => p.Description))
                    : "No tags / pre-requisites";

                PrereqText.Text = scenario.Status ?? "draft";

                //
                // 3) Steps (MAP Step → Description)
                //
                var formattedSteps = scenario.Steps
                    .Select(s => new
                    {
                        Index = s.Index,
                        Description = s.Description ?? "",                 // <-- THIS IS WHAT YOU WANT
                        TestDataText = string.IsNullOrWhiteSpace(s.TestDataText)
                            ? "— None —"
                            : s.TestDataText
                    })
                    .ToList();

                StepsDataGrid.ItemsSource = formattedSteps;
            }
            catch (Exception ex)
            {
                StepsDataGrid.ItemsSource = new[]
                {
            new { Index = 0, Description = ex.Message, TestDataText = "" }
        };
            }
        }

    }
}
