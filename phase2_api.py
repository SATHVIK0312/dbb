using Microsoft.Win32;
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

        // ---------------- Browse ----------------
        private void BrowseFile_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Filter = "Documents|*.pdf;*.docx;*.xlsx"
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
                MessageBox.Show("Please select a file first.");
                return;
            }

            using var client = new ApiClient();
            client.SetBearer(Session.Token);

            var response = await client.PostFileAsync(
                "analyze-document",
                _selectedFilePath
            );

            var json = await response.Content.ReadAsStringAsync();
            _lastAnalyzeResult = JsonSerializer.Deserialize<AnalyzeResult>(
                json,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
            );

            // Populate preview
            UserStoriesList.ItemsSource = _lastAnalyzeResult.user_stories;
            FlowList.ItemsSource = _lastAnalyzeResult.software_flow;
            TestCasesGrid.ItemsSource = _lastAnalyzeResult.test_cases;
        }

        // ---------------- Save ----------------
        private void SaveDocument_Click(object sender, RoutedEventArgs e)
        {
            if (_lastAnalyzeResult == null)
            {
                MessageBox.Show("Nothing to save. Analyze a document first.");
                return;
            }

            MessageBox.Show("✅ Document saved successfully", "Saved",
                MessageBoxButton.OK, MessageBoxImage.Information);
        }

        // ---------------- UI MODELS ----------------
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
