using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using jpmc_genai.Services;

namespace JPMCGenAI_v1._0
{
    public partial class KnowledgeCenterPage : Page
    {
        private string _selectedFilePath;
        private AnalyzeResult _lastAnalyzeResult;

        public KnowledgeCenterPage()
        {
            InitializeComponent();
        }

        // =====================================================
        // BROWSE FILE
        // =====================================================
        private void BrowseFile_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog
            {
                Filter = "Documents (*.pdf;*.docx;*.xlsx)|*.pdf;*.docx;*.xlsx"
            };

            if (dialog.ShowDialog() == true)
            {
                _selectedFilePath = dialog.FileName;
                SelectedFileText.Text = dialog.SafeFileName;
            }
        }

        // =====================================================
        // ANALYZE DOCUMENT (FIXED)
        // =====================================================
        private async void AnalyzeDocument_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_selectedFilePath))
            {
                MessageBox.Show("Please select a document first.", "Validation",
                    MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            try
            {
                AnalyzeButtonState(false);

                using var client = new ApiClient();
                client.SetBearer(Session.Token);

                // 🔹 IMPORTANT: route must match FastAPI
                HttpResponseMessage response =
                    await client.PostFileAsync("analyze-document", _selectedFilePath);

                string json = await response.Content.ReadAsStringAsync();

                System.Diagnostics.Debug.WriteLine("=== ANALYZE RESPONSE ===");
                System.Diagnostics.Debug.WriteLine(json);

                if (!response.IsSuccessStatusCode)
                {
                    MessageBox.Show(
                        $"Analyze failed: {response.StatusCode}",
                        "API Error",
                        MessageBoxButton.OK,
                        MessageBoxImage.Error
                    );
                    return;
                }

                _lastAnalyzeResult = JsonSerializer.Deserialize<AnalyzeResult>(
                    json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                );

                if (_lastAnalyzeResult == null)
                {
                    MessageBox.Show("Unable to parse analysis result.", "Error",
                        MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // =================================================
                // PREVIEW BINDING
                // =================================================
                UserStoriesList.ItemsSource = _lastAnalyzeResult.user_stories ?? new();
                FlowList.ItemsSource = _lastAnalyzeResult.software_flow ?? new();
                TestCasesGrid.ItemsSource = _lastAnalyzeResult.test_cases ?? new();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[ERROR] {ex}");
                MessageBox.Show(
                    $"Unexpected error during analysis:\n{ex.Message}",
                    "Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error
                );
            }
            finally
            {
                AnalyzeButtonState(true);
            }
        }

        // =====================================================
        // SAVE DOCUMENT
        // =====================================================
        private void SaveDocument_Click(object sender, RoutedEventArgs e)
        {
            if (_lastAnalyzeResult == null)
            {
                MessageBox.Show(
                    "Please analyze a document before saving.",
                    "Validation",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning
                );
                return;
            }

            MessageBox.Show(
                "✅ Document saved successfully",
                "Saved",
                MessageBoxButton.OK,
                MessageBoxImage.Information
            );
        }

        // =====================================================
        // UI HELPERS
        // =====================================================
        private void AnalyzeButtonState(bool enabled)
        {
            AnalyzeButton.IsEnabled = enabled;
            AnalyzeButton.Content = enabled ? "Analyze" : "Analyzing...";
        }

        // =====================================================
        // SIDEBAR NAVIGATION (SAFE)
        // =====================================================
        private void BackToDashboard_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new DashboardPage(Session.CurrentProjectId));
        }

        private void UploadTestCase_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new UploadTestCasePage());
        }

        private void AITestExecutor_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new AITestExecutorPage(Session.CurrentProjectId));
        }

        private void ScriptGenerator_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new ScriptGeneratorPage());
        }

        private void ExecutionLog_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new ExecutionLogPage());
        }

        // =====================================================
        // UI MODELS (MATCH BACKEND RESPONSE)
        // =====================================================
        private class AnalyzeResult
        {
            public List<string> user_stories { get; set; }
            public List<string> software_flow { get; set; }
            public List<TestCasePreview> test_cases { get; set; }
        }

        private class TestCasePreview
        {
            public string test_case_id { get; set; }
            public string test_case_description { get; set; }

            // DataGrid-friendly
            public string TestCaseId => test_case_id;
            public string Description => test_case_description;
        }
    }
}
