using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using jpmc_genai.Services;

namespace JPMCGenAI_v1._0
{
    public partial class DashboardPage : Page
    {
        private readonly string _projectId;

        public DashboardPage(string projectId)
        {
            InitializeComponent();
            _projectId = projectId;
            var project = Session.CurrentUser?.projects?.FirstOrDefault(p => p.projectid == projectId);
            ProjectTitleTextBlock.Text = project?.title ?? "Project";
            ProjectDetailsTextBlock.Text = $"ID: {projectId}\nType: {project?.projecttype}\nStarted: {project?.startdate}";

            // Initialize asynchronously
            _ = LoadSummaryAsync();
        }

        private async Task LoadSummaryAsync()
        {
            try
            {
                using var client = new ApiClient();
                client.SetBearer(Session.Token);
                var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };

                var summaryResp = await client.GetAsync($"projects/{_projectId}/summary");

                var summaryJson = await summaryResp.Content.ReadAsStringAsync();
                System.Diagnostics.Debug.WriteLine($"[DEBUG] API Response Status: {summaryResp.StatusCode}");
                System.Diagnostics.Debug.WriteLine($"[DEBUG] API Response Content: {summaryJson}");

                if (summaryResp.IsSuccessStatusCode)
                {
                    var summary = JsonSerializer.Deserialize<ProjectSummary>(summaryJson, options);

                    System.Diagnostics.Debug.WriteLine($"[DEBUG] Deserialized Summary: users={summary?.users_count}, testcases={summary?.testcases_count}");

                    if (summary != null)
                    {
                        UsersCountTextBlock.Text = summary.users_count.ToString();
                        TestCasesCountTextBlock.Text = summary.testcases_count.ToString();
                        TotalExecutionsTextBlock.Text = summary.total_executions.ToString();
                        SuccessfulExecutionsTextBlock.Text = summary.successful_executions.ToString();
                        FailedExecutionsTextBlock.Text = summary.failed_executions.ToString();
                    }
                    else
                    {
                        SetDefaultSummaryValues();
                    }
                }
                else
                {
                    System.Diagnostics.Debug.WriteLine($"[DEBUG] API call failed with status: {summaryResp.StatusCode}");
                    SetDefaultSummaryValues();
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[DEBUG] Exception in LoadSummaryAsync: {ex.Message}");
                SetDefaultSummaryValues();
            }
        }

        private void SetDefaultSummaryValues()
        {
            UsersCountTextBlock.Text = "—";
            TestCasesCountTextBlock.Text = "—";
            TotalExecutionsTextBlock.Text = "—";
            SuccessfulExecutionsTextBlock.Text = "—";
            FailedExecutionsTextBlock.Text = "—";
        }

        private void BackToProjects_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new ProjectPage());
        }

        private void AITestExecutor_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new AITestExecutorPage(_projectId));
        }

        private void ScriptGenerator_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new ScriptGeneratorPage());
        }

        private void ExecutionLog_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new ExecutionLogPage());
        }

        private void UploadTestCase_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new UploadTestCasePage());
        }

        private void ChangeProject_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new ProjectPage());
        }

        private class ProjectSummary
        {
            public string projectid { get; set; } = string.Empty;
            public int users_count { get; set; }
            public int testcases_count { get; set; }
            public int total_executions { get; set; }
            public int successful_executions { get; set; }
            public int failed_executions { get; set; }
        }

        private void Button_Click(object sender, RoutedEventArgs e)
        {

        }
    }
}
