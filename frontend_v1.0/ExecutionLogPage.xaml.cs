using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using JPMCGenAI_v1._0.Services;

namespace JPMCGenAI_v1._0
{
    // =====================================================================
    // MODELS
    // =====================================================================

    public class ReusableMethodsResponse
    {
        public string Testcase_Id { get; set; }
        public List<ReusableMethodDto> Results { get; set; }
    }

    public class SimpleScriptResponse
    {
        public string Testcase_Id { get; set; } = "";
        public string Script_Type { get; set; } = "";
        public string Script_Lang { get; set; } = "";
        public string Generated_Script { get; set; } = "";
    }

    // =====================================================================
    // MAIN PAGE - ExecutionLogPage
    // =====================================================================
    public partial class ExecutionLogPage : Page
    {
        private readonly ApiClient _apiClient;
        private readonly ObservableCollection<ExecutionLog> _executionLogs;
        private ExecutionLog _selectedExecution;
        private TestPlan _currentTestPlan;

        public ExecutionLogPage()
        {
            InitializeComponent();
            _apiClient = new ApiClient();
            _executionLogs = new ObservableCollection<ExecutionLog>();
            ExecutionLogDataGrid.ItemsSource = _executionLogs;

            // Initial UI state
            GenerateScriptButton.IsEnabled = false;
            SelectedExecutionInfo.Text = "Double-click a row to select an execution and generate script";
        }

        private void Page_Loaded(object sender, RoutedEventArgs e)
        {
            LoadProjectInfo();
            LoadExecutionLogs();
        }

        private void LoadProjectInfo()
        {
            if (Session.CurrentProject != null)
            {
                ProjectTitleTextBlock.Text = Session.CurrentProject.title;
                ProjectDetailsTextBlock.Text =
                    $"Type: {Session.CurrentProject.projecttype}\nStarted: {Session.CurrentProject.startdate}";
            }
        }

        private async void LoadExecutionLogs()
        {
            try
            {
                StatusTextBlock.Text = "Loading execution history...";
                _apiClient.SetBearer(Session.Token);

                var response = await _apiClient.GetAsync("ExecutionLogs");

                if (response.IsSuccessStatusCode)
                {
                    var content = await response.Content.ReadAsStringAsync();
                    var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
                    var logs = JsonSerializer.Deserialize<List<ExecutionLog>>(content, options);

                    _executionLogs.Clear();
                    foreach (var log in logs.OrderByDescending(l => l.datestamp).ThenByDescending(l => l.exetime))
                    {
                        _executionLogs.Add(log);
                    }

                    StatusTextBlock.Text = $"Loaded {logs.Count} execution records";
                }
                else
                {
                    StatusTextBlock.Text = "Failed to load execution logs";
                }
            }
            catch (Exception ex)
            {
                StatusTextBlock.Text = "Error loading logs";
                MessageBox.Show($"Error: {ex.Message}");
            }
        }

        // =====================================================================
        // DOUBLE-CLICK ROW → SELECT EXECUTION
        // =====================================================================
        private void ExecutionLogDataGrid_DoubleClick(object sender, MouseButtonEventArgs e)
        {
            var row = ItemsControl.ContainerFromElement(
                sender as DataGrid, e.OriginalSource as DependencyObject) as DataGridRow;

            if (row == null || row.Item is not ExecutionLog log) return;

            _selectedExecution = log;
            GenerateScriptButton.IsEnabled = true;

            SelectedExecutionInfo.Text = 
                $"Selected → Test Case: {log.testcaseid} | Execution ID: {log.exeid} | Status: {log.status}";
        }

        // =====================================================================
        // GENERATE SCRIPT BUTTON CLICK
        // =====================================================================
        private async void GenerateScript_Click(object sender, RoutedEventArgs e)
        {
            if (_selectedExecution == null)
            {
                MessageBox.Show("Please double-click a row to select an execution first.");
                return;
            }

            string testCaseId = _selectedExecution.testcaseid;

            try
            {
                StatusTextBlock.Text = $"Fetching test plan for {testCaseId}...";
                _apiClient.SetBearer(Session.Token);

                // CORRECT API CALL → /testplan/{testcase_id}
                var response = await _apiClient.GetAsync($"testplan/{testCaseId}");

                if (!response.IsSuccessStatusCode)
                {
                    var error = await response.Content.ReadAsStringAsync();
                    MessageBox.Show($"Failed to fetch test plan:\n{response.StatusCode}\n{error}");
                    StatusTextBlock.Text = "Error fetching test plan";
                    return;
                }

                var json = await response.Content.ReadAsStringAsync();
                var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };

                _currentTestPlan = JsonSerializer.Deserialize<TestPlan>(json, options);

                if (_currentTestPlan == null)
                {
                    MessageBox.Show("Received empty or invalid test plan data.");
                    StatusTextBlock.Text = "Invalid test plan data";
                    return;
                }

                // Get user preferences
                bool includePrereq = PrereqSelector.SelectedIndex == 0; // First item = Include
                string scriptType = (ScriptTypeSelector.SelectedItem as ComboBoxItem)?.Content?.ToString().ToLower() ?? "playwright";
                string scriptLang = (ScriptLangSelector.SelectedItem as ComboBoxItem)?.Content?.ToString().ToLower() ?? "python";

                StatusTextBlock.Text = "Generating script...";

                var payload = new
                {
                    pretestid_steps = _currentTestPlan.pretestid_steps ?? new Dictionary<string, Dictionary<string, string>>(),
                    pretestid_scripts = _currentTestPlan.pretestid_scripts ?? new Dictionary<string, string>(),
                    current_testid = testCaseId,
                    current_bdd_steps = _currentTestPlan.current_bdd_steps ?? new Dictionary<string, string>()
                };

                var content = new StringContent(
                    JsonSerializer.Serialize(payload),
                    System.Text.Encoding.UTF8,
                    "application/json");

                var scriptResponse = await _apiClient.PostAsync(
                    $"generate-test-script/{testCaseId}" +
                    $"?script_type={scriptType}&script_lang={scriptLang}&include_prereq={includePrereq}",
                    content);

                if (!scriptResponse.IsSuccessStatusCode)
                {
                    var err = await scriptResponse.Content.ReadAsStringAsync();
                    MessageBox.Show($"Script generation failed:\n{err}");
                    StatusTextBlock.Text = "Script generation failed";
                    return;
                }

                var resultJson = await scriptResponse.Content.ReadAsStringAsync();
                var scriptResult = JsonSerializer.Deserialize<SimpleScriptResponse>(resultJson, options);

                if (string.IsNullOrWhiteSpace(scriptResult?.Generated_Script))
                {
                    MessageBox.Show("Generated script is empty.");
                    return;
                }

                // Show generated script + execution log
                ShowSimpleScriptDialog(
                    testCaseId: testCaseId,
                    script: scriptResult.Generated_Script,
                    executionLog: _selectedExecution.output ?? "No execution output recorded."
                );

                StatusTextBlock.Text = "Script generated successfully!";
            }
            catch (Exception ex)
            {
                StatusTextBlock.Text = "Error occurred";
                MessageBox.Show($"Error:\n{ex.Message}");
            }
        }

        // =====================================================================
        // SHOW SCRIPT + EXECUTION LOG + REUSABLE METHODS BUTTON
        // =====================================================================
        private void ShowSimpleScriptDialog(string testCaseId, string script, string executionLog)
        {
            var win = new Window
            {
                Title = $"Generated Script - {testCaseId}",
                Width = 1000,
                Height = 750,
                Background = new SolidColorBrush(Color.FromRgb(30, 30, 30)),
                Foreground = Brushes.White,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Owner = Window.GetWindow(this),
                ResizeMode = ResizeMode.CanResizeWithGrip
            };

            var scroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
            var stack = new StackPanel { Margin = new Thickness(25) };

            stack.Children.Add(new TextBlock
            {
                Text = "Generated Automation Script",
                FontSize = 18,
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0, 0, 0, 10)
            });

            stack.Children.Add(new TextBox
            {
                Text = script,
                IsReadOnly = true,
                AcceptsReturn = true,
                FontFamily = new FontFamily("Consolas"),
                Background = new SolidColorBrush(Color.FromRgb(40, 40, 40)),
                Foreground = Brushes.Cyan,
                Padding = new Thickness(10),
                Margin = new Thickness(0, 0, 0, 20),
                Height = 360
            });

            stack.Children.Add(new TextBlock
            {
                Text = "Execution Log Output",
                FontSize = 16,
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 10, 0, 8)
            });

            stack.Children.Add(new TextBox
            {
                Text = executionLog,
                IsReadOnly = true,
                AcceptsReturn = true,
                FontFamily = new FontFamily("Consolas"),
                Background = new SolidColorBrush(Color.FromRgb(40, 40, 40)),
                Foreground = Brushes.LightGreen,
                Padding = new Thickness(10),
                Height = 180
            });

            var btnPanel = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                HorizontalAlignment = HorizontalAlignment.Right,
                Margin = new Thickness(0, 25, 0, 10)
            };

            var checkBtn = new Button
            {
                Content = "Check Reusable Methods",
                Background = Brushes.Orange,
                Foreground = Brushes.White,
                Padding = new Thickness(16, 10),
                Margin = new Thickness(0, 0, 12, 0)
            };
            checkBtn.Click += async (_, __) => await CheckReusableMethods(testCaseId, script);

            var downloadBtn = new Button
            {
                Content = "Download Script",
                Background = Brushes.DeepSkyBlue,
                Foreground = Brushes.White,
                Padding = new Thickness(16, 10),
                Margin = new Thickness(0, 0, 12, 0)
            };
            downloadBtn.Click += (_, __) => DownloadScript(testCaseId, script);

            var closeBtn = new Button
            {
                Content = "Close",
                Background = Brushes.Gray,
                Foreground = Brushes.White,
                Padding = new Thickness(16, 10)
            };
            closeBtn.Click += (_, __) => win.Close();

            btnPanel.Children.Add(checkBtn);
            btnPanel.Children.Add(downloadBtn);
            btnPanel.Children.Add(closeBtn);

            stack.Children.Add(btnPanel);
            scroll.Content = stack;
            win.Content = scroll;
            win.ShowDialog();
        }

        private async Task CheckReusableMethods(string testCaseId, string script)
        {
            // Same as before — kept for compatibility
            try
            {
                _apiClient.SetBearer(Session.Token);

                List<string> bddSteps = _currentTestPlan?.current_bdd_steps?.Keys.ToList() ?? new List<string>();

                var payload = new
                {
                    testcase_id = testCaseId,
                    generated_script = script,
                    bdd_steps = bddSteps
                };

                var content = new StringContent(JsonSerializer.Serialize(payload), System.Text.Encoding.UTF8, "application/json");
                var response = await _apiClient.PostAsync("reusable-methods/check", content);

                if (!response.IsSuccessStatusCode)
                {
                    MessageBox.Show("Error: " + await response.Content.ReadAsStringAsync());
                    return;
                }

                var raw = await response.Content.ReadAsStringAsync();
                var data = JsonSerializer.Deserialize<ReusableMethodsResponse>(raw,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                if (data?.Results == null || data.Results.Count == 0)
                {
                    MessageBox.Show("No reusable methods detected for this script.");
                    return;
                }

                var view = new ReusableMethodViewWindow(data.Results);
                view.ShowDialog();
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error: " + ex.Message);
            }
        }

        private void DownloadScript(string testCaseId, string script)
        {
            try
            {
                string fileName = $"{testCaseId}_script_{DateTime.Now:yyyyMMdd_HHmmss}.txt";
                string path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), fileName);
                File.WriteAllText(path, script);
                MessageBox.Show($"Script saved to Desktop:\n{path}", "Saved", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Save failed: " + ex.Message);
            }
        }

        // =====================================================================
        // NAVIGATION (unchanged)
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

        private void ChangeProject_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(new ProjectPage());
    }

    // =====================================================================
    // REUSABLE METHOD DTO (must be public or internal)
    // =====================================================================
    public class ReusableMethodDto
    {
        public string step_label { get; set; }
        public string step_details { get; set; }
        public string query { get; set; }
        public string method_name { get; set; }
        public string class_name { get; set; }
        public double score { get; set; }
        public string signature { get; set; }
        public string method_code { get; set; }
        public string Query => query;
        public string Method_Name => method_name;
        public string Class_Name => class_name;
        public string Match_Percentage => $"{score:P1}";
        public string Full_Signature => signature;
    }
}
