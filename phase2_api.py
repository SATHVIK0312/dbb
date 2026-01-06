using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using JPMCGenAI_v1._0.Services;

namespace JPMCGenAI_v1._0
{
    // Move data models outside the page class so they can be shared
    public class UserStory
    {
        public int id { get; set; }
        public int document_id { get; set; }
        public string story { get; set; }
    }

    public class SoftwareFlow
    {
        public int id { get; set; }
        public int document_id { get; set; }
        public string step { get; set; }
    }

    public class TestCase
    {
        public int id { get; set; }
        public int document_id { get; set; }
        public string test_case_id { get; set; }
        public string description { get; set; }
        public string pre_req_id { get; set; }
        public string pre_req_desc { get; set; }
        public string tags { get; set; }
        public string steps { get; set; }
        public string arguments { get; set; }
    }

    public partial class KnowledgeCenterPage : Page
    {
        private readonly string _projectId;
        private string _selectedFilePath;

        public KnowledgeCenterPage(string projectId = "")
        {
            InitializeComponent();
            _projectId = projectId;
        }

        // ---------------- Page Load ----------------
        private async void Page_Loaded(object sender, RoutedEventArgs e)
        {
            LoadProjectInfo();
            await LoadAllKnowledgeData();
        }

        // ---------------- Load Project Info ----------------
        private void LoadProjectInfo()
        {
            if (Session.CurrentProject != null)
            {
                // Use the available property from Session.CurrentProject
                ProjectTitleTextBlock.Text = Session.CurrentProject.name ?? "Current Project";
                ProjectDetailsTextBlock.Text = $"ID: {Session.CurrentProject.projectid}";
            }
            else
            {
                ProjectTitleTextBlock.Text = "No Project";
                ProjectDetailsTextBlock.Text = "Please select a project";
            }
        }

        // ---------------- Load All Data ----------------
        private async System.Threading.Tasks.Task LoadAllKnowledgeData()
        {
            try
            {
                using var client = new ApiClient();
                client.SetBearer(Session.Token);

                HttpResponseMessage response = await client.GetAsync("knowledge-center/all-data");
                string json = await response.Content.ReadAsStringAsync();

                if (!response.IsSuccessStatusCode)
                {
                    MessageBox.Show($"Failed to load data: {response.StatusCode}");
                    return;
                }

                var result = JsonSerializer.Deserialize<KnowledgeCenterResponse>(
                    json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                );

                if (result?.data != null)
                {
                    // Update counts
                    UserStoriesCountText.Text = result.counts.user_stories.ToString();
                    SoftwareFlowsCountText.Text = result.counts.software_flows.ToString();
                    TestCasesCountText.Text = result.counts.test_cases.ToString();

                    // Update grids
                    UserStoriesGrid.ItemsSource = result.data.user_stories;
                    SoftwareFlowsGrid.ItemsSource = result.data.software_flows;
                    TestCasesGrid.ItemsSource = result.data.test_cases;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error loading knowledge data: {ex.Message}");
            }
        }

        // ---------------- Browse ----------------
        private void BrowseFile_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Filter = "Documents (*.pdf;*.docx;*.xlsx)|*.pdf;*.docx;*.xlsx"
            };

            if (dlg.ShowDialog() == true)
            {
                _selectedFilePath = dlg.FileName;
                SelectedFileText.Text = dlg.SafeFileName;
            }
        }

        // ---------------- Analyze ----------------
        private async void AnalyzeDocument_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_selectedFilePath))
            {
                MessageBox.Show("Please select a document first.");
                return;
            }

            try
            {
                // UI state
                AnalyzeButton.IsEnabled = false;
                AnalyzeButton.Content = "Analyzing...";

                // Force UI refresh
                await Dispatcher.InvokeAsync(() => { });

                using var client = new ApiClient();
                client.SetBearer(Session.Token);

                HttpResponseMessage response =
                    await client.PostFileAsync("analyze-document", _selectedFilePath);

                string json = await response.Content.ReadAsStringAsync();

                if (!response.IsSuccessStatusCode)
                {
                    MessageBox.Show($"Analyze failed: {response.StatusCode}\n{json}");
                    return;
                }

                var analyzeResult = JsonSerializer.Deserialize<AnalyzeResponse>(
                    json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                );

                if (analyzeResult?.document_id == null)
                {
                    MessageBox.Show("Failed to parse analyze response.");
                    return;
                }

                // Show popup with document details
                await ShowDocumentDetailsPopup(analyzeResult.document_id);

                // Reload main data
                await LoadAllKnowledgeData();
                
                // Clear selection
                _selectedFilePath = null;
                SelectedFileText.Text = "No file selected";
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error: {ex.Message}");
            }
            finally
            {
                AnalyzeButton.IsEnabled = true;
                AnalyzeButton.Content = "Analyze";
            }
        }

        // ---------------- Show Document Details Popup ----------------
        private async System.Threading.Tasks.Task ShowDocumentDetailsPopup(int documentId)
        {
            try
            {
                using var client = new ApiClient();
                client.SetBearer(Session.Token);

                // Fetch all details for the document
                var userStoriesTask = client.GetAsync($"documents/{documentId}/user-stories");
                var softwareFlowTask = client.GetAsync($"documents/{documentId}/software-flow");
                var testCasesTask = client.GetAsync($"documents/{documentId}/test-cases");

                await System.Threading.Tasks.Task.WhenAll(userStoriesTask, softwareFlowTask, testCasesTask);

                var userStoriesJson = await userStoriesTask.Result.Content.ReadAsStringAsync();
                var softwareFlowJson = await softwareFlowTask.Result.Content.ReadAsStringAsync();
                var testCasesJson = await testCasesTask.Result.Content.ReadAsStringAsync();

                var userStories = JsonSerializer.Deserialize<List<UserStory>>(
                    userStoriesJson,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                );

                var softwareFlows = JsonSerializer.Deserialize<List<SoftwareFlow>>(
                    softwareFlowJson,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                );

                var testCases = JsonSerializer.Deserialize<List<TestCase>>(
                    testCasesJson,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                );

                // Show popup window
                var popup = new DocumentDetailsWindow(documentId, userStories, softwareFlows, testCases);
                popup.ShowDialog();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error loading document details: {ex.Message}");
            }
        }

        // =====================================================================
        // NAVIGATION
        // =====================================================================
        private void BackToDashboard_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(Session.CurrentProject != null
                ? new DashboardPage(Session.CurrentProject.projectid)
                : new ProjectPage());

        private void AITestExecutor_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(Session.CurrentProject != null
                ? new AITestExecutorPage(Session.CurrentProject.projectid)
                : new ProjectPage());

        private void ScriptGenerator_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(new ScriptGeneratorPage());

        private void UploadTestCase_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(new UploadTestCasePage());

        private void ExecutionLog_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(new ExecutionLogPage());

        private void ChangeProject_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(new ProjectPage());

        // ---------------- RESPONSE MODELS ----------------
        
        private class KnowledgeCenterResponse
        {
            public string status { get; set; }
            public CountsData counts { get; set; }
            public AllData data { get; set; }
        }

        private class CountsData
        {
            public int user_stories { get; set; }
            public int software_flows { get; set; }
            public int test_cases { get; set; }
        }

        private class AllData
        {
            public List<UserStory> user_stories { get; set; }
            public List<SoftwareFlow> software_flows { get; set; }
            public List<TestCase> test_cases { get; set; }
        }

        private class AnalyzeResponse
        {
            public string status { get; set; }
            public int document_id { get; set; }
            public string message { get; set; }
        }
    }
}
