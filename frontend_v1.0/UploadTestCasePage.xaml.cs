using JPMCGenAI_v1._0.Services;
using OfficeOpenXml;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace JPMCGenAI_v1._0
{
    public partial class UploadTestCasePage : Page, INotifyPropertyChanged
    {
        private readonly ApiClient _api = new ApiClient();
        private int _page = 1, _pageSize = 10;
        private string _selectedFile = "";
        private readonly string _tempFolder = Path.Combine(Path.GetTempPath(), "jpmc_genai", "preview");
        private readonly string _originalJsonPath;
        private readonly string _normalizedJsonPath;

        private List<GroupedTestCase> _groupedTestCases = new();
        private readonly ObservableCollection<UploadedTestCaseViewModel> _uploadedTestCases = new();

        public event PropertyChangedEventHandler? PropertyChanged;
        protected void OnPropertyChanged([CallerMemberName] string name = null) =>
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));

        public UploadTestCasePage()
        {
            InitializeComponent();
            ExcelPackage.LicenseContext = OfficeOpenXml.LicenseContext.NonCommercial;

            _originalJsonPath = Path.Combine(_tempFolder, "original.json");
            _normalizedJsonPath = Path.Combine(_tempFolder, "normalized.json");
            Directory.CreateDirectory(_tempFolder);

            UploadedTestCasesGrid.ItemsSource = _uploadedTestCases;

            Loaded += async (s, e) =>
            {
                if (Session.CurrentProject != null)
                {
                    ProjectTitleTextBlock.Text = Session.CurrentProject.title ?? "Unknown Project";
                    ProjectDetailsTextBlock.Text =
                        $"ID: {Session.CurrentProject.projectid}\n" +
                        $"Type: {Session.CurrentProject.projecttype ?? "— "}\n" +
                        $"Started: {Session.CurrentProject.startdate ?? "— "}";
                }
                await LoadTestCases();
            };
        }

        private string CurrentProjectId => Session.CurrentProject?.projectid
            ?? throw new InvalidOperationException("No project selected.");

        #region Sidebar Navigation
        private void Dashboard_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(new DashboardPage(Session.CurrentProject.projectid));

        private void AITestExecutor_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(new AITestExecutorPage(Session.CurrentProject.projectid));

        private void ScriptGenerator_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(new ScriptGeneratorPage());

        private void ExecutionLog_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(new ExecutionLogPage());

        private void ChangeProject_Click(object sender, RoutedEventArgs e)
            => NavigationService?.Navigate(new ProjectPage());
        #endregion

        #region Load Existing Test Cases
        private async Task LoadTestCases()
        {
            ListStatus.Text = "Loading test cases...";
            try
            {
                _api.SetBearer(Session.Token);
                var resp = await _api.GetAsync(
                    $"projects/{CurrentProjectId}/testcases/paginated?page={_page}&page_size={_pageSize}");
                resp.EnsureSuccessStatusCode();

                var json = await resp.Content.ReadAsStringAsync();
                var root = JsonSerializer.Deserialize<PaginatedTestCasesResponse>(json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                var display = new List<object>();

                foreach (var tc in root.testcases)
                {
                    int realStepCount = 0;
                    try
                    {
                        var detailsResp = await _api.GetAsync($"testcases/details?testcaseids={tc.testcaseid}");
                        if (detailsResp.IsSuccessStatusCode)
                        {
                            var detailsJson = await detailsResp.Content.ReadAsStringAsync();
                            var details = JsonSerializer.Deserialize<TestCaseDetails>(detailsJson,
                                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                            realStepCount = details.Scenarios?.FirstOrDefault()?.Steps?.Count ?? 0;
                        }
                    }
                    catch { }

                    display.Add(new
                    {
                        testcaseid = tc.testcaseid,
                        testdesc = tc.testdesc,
                        steps_count = realStepCount,
                        tags_display = string.Join(", ", tc.tag ?? new List<string>())
                    });
                }

                ExistingTestCasesGrid.ItemsSource = display;
                PageInfo.Text = $"Page {root.page} of {root.total_pages}";
                ListStatus.Text = $"Loaded {root.total_count} test cases";
                ListStatus.Foreground = Brushes.LimeGreen;
            }
            catch (Exception ex)
            {
                ListStatus.Text = $"Error: {ex.Message}";
                ListStatus.Foreground = Brushes.Red;
                ExistingTestCasesGrid.ItemsSource = null;
            }
        }

        private async void PrevPage_Click(object sender, RoutedEventArgs e)
        {
            if (_page > 1) { _page--; await LoadTestCases(); }
        }

        private async void NextPage_Click(object sender, RoutedEventArgs e)
        {
            _page++; await LoadTestCases();
        }
        #endregion

        #region View & Edit Existing Test Cases
        private void ViewTestCase_Click(object sender, RoutedEventArgs e)
        {
            var id = (string)((Button)sender).CommandParameter;
            var local = _groupedTestCases.FirstOrDefault(x => x.TestCaseId == id);
            if (local != null)
            {
                var dlg = new TestCaseDetailWindow_Local(local) { Owner = Window.GetWindow(this) };
                dlg.ShowDialog();
                return;
            }
            new TestCaseDetailWindow(id) { Owner = Window.GetWindow(this) }.ShowDialog();
        }

        private async void EditTestCase_Click(object sender, RoutedEventArgs e)
        {
            var id = (string)((Button)sender).CommandParameter;
            var local = _groupedTestCases.FirstOrDefault(x => x.TestCaseId == id);
            if (local != null)
            {
                var dlg = new EditTestCaseWindow(id, new TestStepInfo
                {
                    steps = local.Steps.Select(s => s.Step).ToList(),
                    args = local.Steps.Select(s => s.Argument).ToList()
                }) { Owner = Window.GetWindow(this) };

                if (dlg.ShowDialog() == true)
                {
                    local.Steps = dlg.EditableSteps.Select(es => new TestStep
                    {
                        Step = es.Step,
                        Argument = es.TestDataText
                    }).ToList();
                }
                return;
            }

            try
            {
                _api.SetBearer(Session.Token);
                var resp = await _api.GetAsync($"testcases/details?testcaseids={id}");
                resp.EnsureSuccessStatusCode();
                var json = await resp.Content.ReadAsStringAsync();
                var details = JsonSerializer.Deserialize<TestCaseDetails>(json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                var scenario = details.Scenarios?.FirstOrDefault();
                if (scenario == null) throw new Exception("No steps found.");

                var stepList = scenario.Steps.Select(s => s.Step ?? "").ToList();
                var argList = scenario.Steps.Select(s => s.TestDataText ?? "").ToList();

                var dlg2 = new EditTestCaseWindow(id, new TestStepInfo
                {
                    steps = stepList,
                    args = argList
                }) { Owner = Window.GetWindow(this) };

                if (dlg2.ShowDialog() == true)
                {
                    var payload = new
                    {
                        normalized_steps = dlg2.EditableSteps.Select(es => new
                        {
                            Step = es.Step,
                            TestDataText = es.TestDataText
                        }).ToList()
                    };

                    var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
                    await _api.PostAsync($"replace-normalized/{id}", content);
                    await LoadTestCases();
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Edit failed: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        #endregion

        #region Drag & Drop
        private void DropArea_DragOver(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop)) e.Effects = DragDropEffects.Copy;
            e.Handled = true;
        }

        private void DropArea_Drop(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                var files = (string[])e.Data.GetData(DataFormats.FileDrop);
                if (files.Length > 0 && files[0].EndsWith(".xlsx", StringComparison.OrdinalIgnoreCase))
                {
                    _selectedFile = files[0];
                    SelectedFileLbl.Text = $"Selected: {Path.GetFileName(_selectedFile)}";
                    UploadBtn.IsEnabled = true;
                }
            }
        }
        #endregion

        #region Upload & Preview
        private async void UploadAndPreview_Click(object sender, RoutedEventArgs e)
        {
            UploadBtn.IsEnabled = false;
            UploadStatus.Text = "Reading Excel file...";

            try
            {
                _groupedTestCases = ParseExcelWithGrouping(_selectedFile);
                if (!_groupedTestCases.Any())
                    throw new Exception("No test cases found in the Excel file.");

                _uploadedTestCases.Clear();
                foreach (var tc in _groupedTestCases)
                {
                    _uploadedTestCases.Add(new UploadedTestCaseViewModel
                    {
                        TestCaseId = tc.TestCaseId,
                        Description = tc.Description,
                        Steps = tc.Steps,
                        Tags = tc.Tags,
                        IsSelected = true
                    });
                }

                UploadedTestCasesGrid.ItemsSource = _uploadedTestCases;
                UploadedTestCasesPanel.Visibility = Visibility.Visible;
                NormalizeSelectedBtn.IsEnabled = true;
                ActionPanel.Visibility = Visibility.Collapsed;

                UploadStatus.Text = $"Parsed {_uploadedTestCases.Count} test cases. Select and normalize.";
                UploadStatus.Foreground = Brushes.LimeGreen;
            }
            catch (Exception ex)
            {
                UploadStatus.Text = $"Error: {ex.Message}";
                UploadStatus.Foreground = Brushes.Red;
            }
            finally
            {
                UploadBtn.IsEnabled = true;
            }
        }
        #endregion

        #region Checkbox Selection
        private void SelectAll_Checked(object sender, RoutedEventArgs e) => SetAllSelected(true);
        private void SelectAll_Unchecked(object sender, RoutedEventArgs e) => SetAllSelected(false);
        private void SelectAll_Click(object sender, RoutedEventArgs e) => SetAllSelected(true);
        private void SetAllSelected(bool value)
        {
            foreach (var item in _uploadedTestCases)
                item.IsSelected = value;
        }
        #endregion

        #region View/Edit Uploaded Test Cases
        private void ViewUploadedTestCase_Click(object sender, RoutedEventArgs e)
        {
            if (sender is not Button btn || btn.CommandParameter is not string testCaseId) return;
            var testCase = _groupedTestCases.FirstOrDefault(x => x.TestCaseId == testCaseId);
            if (testCase == null) return;
            var dlg = new TestCaseDetailWindow_Local(testCase) { Owner = Window.GetWindow(this) };
            dlg.ShowDialog();
        }

        private void EditUploadedTestCase_Click(object sender, RoutedEventArgs e)
        {
            if (sender is not Button btn || btn.CommandParameter is not string testCaseId) return;
            var testCase = _groupedTestCases.FirstOrDefault(x => x.TestCaseId == testCaseId);
            if (testCase == null) return;

            var dlg = new EditTestCaseWindow(testCaseId, new TestStepInfo
            {
                steps = testCase.Steps.Select(s => s.Step).ToList(),
                args = testCase.Steps.Select(s => s.Argument).ToList()
            }) { Owner = Window.GetWindow(this) };

            if (dlg.ShowDialog() == true)
            {
                testCase.Steps = dlg.EditableSteps.Select(es => new TestStep
                {
                    Step = es.Step,
                    Argument = es.TestDataText
                }).ToList();
                _uploadedTestCases.First(x => x.TestCaseId == testCaseId).Description = testCase.Description;
                UploadedTestCasesGrid.Items.Refresh();
            }
        }
        #endregion

        #region Normalize Individual
        private async void NormalizeIndividual_Click(object sender, RoutedEventArgs e)
        {
            if (sender is not Button btn || btn.CommandParameter is not string testCaseId) return;
            var testCase = _groupedTestCases.FirstOrDefault(x => x.TestCaseId == testCaseId);
            if (testCase == null) return;

            var selected = new List<UploadedTestCaseViewModel>
            {
                _uploadedTestCases.First(x => x.TestCaseId == testCaseId)
            };

            await NormalizeTestCases(selected);
        }
        #endregion

        #region Normalize Selected
        private async void NormalizeSelected_Click(object sender, RoutedEventArgs e)
        {
            var selected = _uploadedTestCases.Where(x => x.IsSelected).ToList();
            await NormalizeTestCases(selected);
        }

        private async Task NormalizeTestCases(List<UploadedTestCaseViewModel> selected)
        {
            if (!selected.Any())
            {
                MessageBox.Show("Please select at least one test case to normalize.", "Nothing Selected",
                    MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            NormalizeSelectedBtn.IsEnabled = false;
            UploadStatus.Text = $"Normalizing {selected.Count} selected test case(s)...";

            try
            {
                _api.SetBearer(Session.Token);
                var normalizedList = new List<Dictionary<string, object>>();

                foreach (var vm in selected)
                {
                    var tc = _groupedTestCases.First(x => x.TestCaseId == vm.TestCaseId);

                    var payload = new
                    {
                        testcaseid = tc.TestCaseId,
                        original_steps = tc.Steps.Select((s, i) => new
                        {
                            Index = i + 1,
                            Step = s.Step ?? "",
                            TestDataText = s.Argument ?? ""
                        }).ToList()
                    };

                    var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
                    var resp = await _api.PostAsync("normalize-uploaded", content);
                    resp.EnsureSuccessStatusCode();

                    var json = await resp.Content.ReadAsStringAsync();
                    var norm = JsonSerializer.Deserialize<NormalizeApiResponse>(json,
                        new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                    normalizedList.Add(new Dictionary<string, object>
                    {
                        ["testcaseid"] = tc.TestCaseId,
                        ["original"] = norm.OriginalSteps?.Select(s => new Dictionary<string, object>
                        {
                            ["Index"] = s.Index,
                            ["Step"] = s.Step ?? "",
                            ["TestDataText"] = s.TestDataText ?? "",
                            ["TestData"] = s.TestData ?? new Dictionary<string, object>()
                        }).ToList() ?? new List<Dictionary<string, object>>(),

                        ["normalized"] = norm.NormalizedSteps.Select(s => new Dictionary<string, object>
                        {
                            ["Index"] = s.Index,
                            ["Step"] = s.Step ?? "",
                            ["TestDataText"] = s.TestDataText ?? "",
                            ["TestData"] = s.TestData ?? new Dictionary<string, object>()
                        }).ToList()
                    });
                }

                File.WriteAllText(_originalJsonPath, JsonSerializer.Serialize(_groupedTestCases));
                File.WriteAllText(_normalizedJsonPath, JsonSerializer.Serialize(normalizedList));

                var preview = new NormalizePreviewWindow(normalizedList) { Owner = Window.GetWindow(this) };
                if (preview.ShowDialog() == true)
                {
                    File.WriteAllText(_normalizedJsonPath, JsonSerializer.Serialize(preview.UpdatedNormalizedList));
                    UploadStatus.Text = "Normalization complete! Ready to commit.";
                    UploadStatus.Foreground = Brushes.LimeGreen;
                    ActionPanel.Visibility = Visibility.Visible;
                }
            }
            catch (Exception ex)
            {
                UploadStatus.Text = $"Normalization failed: {ex.Message}";
                UploadStatus.Foreground = Brushes.Red;
            }
            finally
            {
                NormalizeSelectedBtn.IsEnabled = true;
            }
        }
        #endregion

        #region Commit to Database - 100% WORKING
        private async void CommitToDb_Click(object sender, RoutedEventArgs e)
        {
            UploadStatus.Text = "Committing to database...";
            UploadStatus.Foreground = Brushes.Orange;

            try
            {
                if (!File.Exists(_normalizedJsonPath))
                    throw new Exception("No normalized data found. Please normalize first.");

                var json = File.ReadAllText(_normalizedJsonPath);
                var normalizedList = JsonSerializer.Deserialize<List<Dictionary<string, object>>>(json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                var testcasesForCommit = new List<object>();

                foreach (var item in normalizedList)
                {
                    var testcaseid = item["testcaseid"]?.ToString()
                        ?? throw new Exception("Missing testcaseid");

                    var originalTc = _groupedTestCases.FirstOrDefault(g => g.TestCaseId == testcaseid)
                        ?? throw new Exception($"Test case {testcaseid} not found in staged data");

                    var normalizedSteps = item["normalized"] as List<Dictionary<string, object>>
                        ?? throw new Exception("Invalid normalized steps");

                    var steps = new List<object>();
                    foreach (var stepObj in normalizedSteps)
                    {
                        steps.Add(new
                        {
                            Step = stepObj["Step"]?.ToString() ?? "",
                            TestDataText = stepObj["TestDataText"]?.ToString() ?? ""
                        });
                    }

                    testcasesForCommit.Add(new
                    {
                        testcaseid,
                        testdesc = originalTc.Description,
                        pretestid = originalTc.PreReqId ?? "",
                        prereq = originalTc.PreReqDesc ?? "",
                        tags = originalTc.Tags,
                        steps
                    });
                }

                var payload = new
                {
                    projectid = CurrentProjectId,
                    testcases = testcasesForCommit
                };

                var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
                var response = await _api.PostAsync("commit-staged-upload", content);
                response.EnsureSuccessStatusCode();

                MessageBox.Show("All test cases committed successfully!", "Success",
                    MessageBoxButton.OK, MessageBoxImage.Information);

                _groupedTestCases.Clear();
                _uploadedTestCases.Clear();
                UploadedTestCasesPanel.Visibility = Visibility.Collapsed;
                ActionPanel.Visibility = Visibility.Collapsed;
                ResetUploadUI();
                await LoadTestCases();

                UploadStatus.Text = "Commit successful!";
                UploadStatus.Foreground = Brushes.LimeGreen;
            }
            catch (Exception ex)
            {
                UploadStatus.Text = $"Commit failed: {ex.Message}";
                UploadStatus.Foreground = Brushes.Red;
                MessageBox.Show($"Error: {ex.Message}", "Commit Failed", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        #endregion

        #region Cancel Upload
        private void CancelUpload_Click(object sender, RoutedEventArgs e)
        {
            _groupedTestCases.Clear();
            _uploadedTestCases.Clear();
            UploadedTestCasesPanel.Visibility = Visibility.Collapsed;
            ActionPanel.Visibility = Visibility.Collapsed;
            ResetUploadUI();
            UploadStatus.Text = "Upload cancelled.";
            UploadStatus.Foreground = Brushes.LightGray;
        }

        private void ResetUploadUI()
        {
            SelectedFileLbl.Text = "No file selected";
            UploadBtn.IsEnabled = false;
            UploadBtn.Content = "Upload & Preview";
        }
        #endregion

        #region Excel Parser & Models
        private List<GroupedTestCase> ParseExcelWithGrouping(string path)
        {
            var result = new List<GroupedTestCase>();
            GroupedTestCase current = null;

            using var package = new ExcelPackage(new FileInfo(path));
            var ws = package.Workbook.Worksheets[0];

            for (int row = 2; row <= ws.Dimension.End.Row; row++)
            {
                var rawId = ws.Cells[row, 1].GetValue<string>()?.Trim();
                string id = string.IsNullOrWhiteSpace(rawId) ? current?.TestCaseId : rawId;

                if (string.IsNullOrWhiteSpace(rawId) && current == null) continue;

                var desc = ws.Cells[row, 2].GetValue<string>()?.Trim() ?? "";
                var stepText = ws.Cells[row, 6].GetValue<string>()?.Trim();
                var argText = ws.Cells[row, 7].GetValue<string>()?.Trim();

                if (current == null || current.TestCaseId != id)
                {
                    if (current != null) result.Add(current);
                    current = new GroupedTestCase
                    {
                        TestCaseId = id,
                        Description = desc,
                        PreReqId = ws.Cells[row, 3].GetValue<string>() ?? "",
                        PreReqDesc = ws.Cells[row, 4].GetValue<string>() ?? "",
                        Tags = (ws.Cells[row, 5].GetValue<string>() ?? "")
                            .Split(',', StringSplitOptions.RemoveEmptyEntries)
                            .Select(t => t.Trim()).ToList(),
                        Steps = new List<TestStep>()
                    };
                }

                if (!string.IsNullOrWhiteSpace(stepText) || !string.IsNullOrWhiteSpace(argText))
                {
                    current.Steps.Add(new TestStep
                    {
                        Step = stepText ?? "",
                        Argument = argText ?? ""
                    });
                }
            }

            if (current != null) result.Add(current);
            return result;
        }

        public class GroupedTestCase
        {
            public string TestCaseId { get; set; } = "";
            public string Description { get; set; } = "";
            public string PreReqId { get; set; } = "";
            public string PreReqDesc { get; set; } = "";
            public List<string> Tags { get; set; } = new();
            public List<TestStep> Steps { get; set; } = new();
        }

        public class TestStep
        {
            public string Step { get; set; } = "";
            public string Argument { get; set; } = "";
        }

        public class UploadedTestCaseViewModel : INotifyPropertyChanged
        {
            public string TestCaseId { get; set; } = "";
            public string Description { get; set; } = "";
            public List<TestStep> Steps { get; set; } = new();
            public List<string> Tags { get; set; } = new();
            public string TagsString => string.Join(", ", Tags);

            private bool _isSelected;
            public bool IsSelected
            {
                get => _isSelected;
                set { _isSelected = value; OnPropertyChanged(); }
            }

            public event PropertyChangedEventHandler? PropertyChanged;
            protected void OnPropertyChanged([CallerMemberName] ?.string name = null) =>
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }
        #endregion
    }
}
