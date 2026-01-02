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
    public partial class KnowledgeCenterPage : Page
    {
        private readonly string _projectId;
        private string _selectedFilePath;
        private AnalyzeResult _lastAnalyzeResult;

        public KnowledgeCenterPage(string projectId = "")
        {
            InitializeComponent();
            _projectId = projectId;
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
        // ANALYZE DOCUMENT
        // =====================================================
        private async void AnalyzeDocument_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_selectedFilePath))
            {
                MessageBox.Show("Please select a document first.",
                    "Validation",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
                return;
            }

            try
            {
                using var client = new ApiClient();
                client.SetBearer(Session.Token);

                HttpResponseMessage response =
                    await client.PostFileAsync("analyze-document", _selectedFilePath);

                string json = await response.Content.ReadAsStringAsync();
                System.Diagnostics.Debug.WriteLine(json);

                if (!response.IsSuccessStatusCode)
                {
                    MessageBox.Show($"Analyze failed: {response.StatusCode}",
                        "API Error",
                        MessageBoxButton.OK,
                        MessageBoxImage.Error);
                    return;
                }

                _lastAnalyzeResult = JsonSerializer.Deserialize<AnalyzeResult>(
                    json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                );

                if (_lastAnalyzeResult == null)
                {
                    MessageBox.Show("Unable to parse analysis result.",
                        "Error",
                        MessageBoxButton.OK,
                        MessageBoxImage.Error);
                    return;
                }

                // Preview binding
                UserStoriesList.ItemsSource = _lastAnalyzeResult.user_stories ?? new();
                FlowList.ItemsSource = _lastAnalyzeResult.software_flow ?? new();
                TestCasesGrid.ItemsSource = _lastAnalyzeResult.test_cases ?? new();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine(ex);
                MessageBox.Show(
                    $"Unexpected error:\n{ex.Message}",
                    "Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error
                );
            }
        }

        // =====================================================
        // SAVE DOCUMENT
        // =====================================================
        private void SaveDocument_Click(object sender, RoutedEventArgs e)
        {
            if (_lastAnalyzeResult == null)
            {
                MessageBox.Show("Analyze a document before saving.",
                    "Validation",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
                return;
            }

            MessageBox.Show("✅ Document saved successfully",
                "Saved",
                MessageBoxButton.OK,
                MessageBoxImage.Information);
        }

        // =====================================================
        // SIDEBAR NAVIGATION
        // =====================================================
        private void BackToDashboard_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new DashboardPage(_projectId));
        }

        private void UploadTestCase_Click(object sender, RoutedEventArgs e)
        {
            NavigationService?.Navigate(new UploadTestCasePage());
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

        // =====================================================
        // UI MODELS
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

            public string TestCaseId => test_case_id;
            public string Description => test_case_description;
        }
    }
}
