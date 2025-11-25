using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Windows;

namespace JPMCGenAI_v1._0
{
    public partial class NormalizePreviewWindow : Window
    {
        private List<Dictionary<string, object>> _data;

        public List<Dictionary<string, object>> UpdatedNormalizedList { get; private set; }

        public NormalizePreviewWindow(List<Dictionary<string, object>> normalizedData)
        {
            InitializeComponent();
            _data = normalizedData;

            if (_data != null && _data.Count > 0)
            {
                System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Received {_data.Count} test cases");
                foreach (var item in _data)
                {
                    System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] TestCase ID: {item["testcaseid"]}");
                    if (item.ContainsKey("original"))
                        System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] - Original steps count: {(item["original"] as IEnumerable)?.Cast<object>().Count() ?? 0}");
                    if (item.ContainsKey("normalized"))
                        System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] - Normalized steps count: {(item["normalized"] as IEnumerable)?.Cast<object>().Count() ?? 0}");
                }

                TestCaseSelector.ItemsSource = _data.Select(x => x["testcaseid"]?.ToString()).ToList();
                TestCaseSelector.SelectedIndex = 0;
            }
            else
            {
                MessageBox.Show("No data to display", "Empty Data", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
        }

        private void TestCaseSelector_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
        {
            if (TestCaseSelector.SelectedItem == null) return;

            try
            {
                string selectedId = TestCaseSelector.SelectedItem.ToString();
                System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Selected: {selectedId}");

                var tc = _data.FirstOrDefault(x => x["testcaseid"]?.ToString() == selectedId);

                if (tc == null)
                {
                    MessageBox.Show($"Test case '{selectedId}' not found in data.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                try
                {
                    var originalSteps = new ObservableCollection<StepModel>();
                    if (tc.ContainsKey("original"))
                    {
                        var originalData = tc["original"];
                        System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Original data type: {originalData?.GetType().Name}");

                        IEnumerable<Dictionary<string, object>> originalList = null;

                        if (originalData is JsonElement je)
                        {
                            originalList = JsonSerializer.Deserialize<List<Dictionary<string, object>>>(je.GetRawText());
                        }
                        else if (originalData is List<Dictionary<string, object>> list)
                        {
                            originalList = list;
                        }
                        else if (originalData is IEnumerable enumerable)
                        {
                            originalList = enumerable.Cast<object>().Select(s => ExtractStepData(s)).Where(s => s != null).ToList();
                        }

                        System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Original steps parsed: {originalList?.Count() ?? 0}");

                        if (originalList != null)
                        {
                            foreach (var step in originalList)
                            {
                                if (step != null)
                                {
                                    var model = new StepModel
                                    {
                                        Index = step.ContainsKey("Index") ? step["Index"]?.ToString() ?? "0" : "0",
                                        Step = step.ContainsKey("Step") ? step["Step"]?.ToString() ?? "" : "",
                                        TestDataText = step.ContainsKey("TestDataText") ? step["TestDataText"]?.ToString() ?? "" : "",
                                        TestData = step.ContainsKey("TestData")
        ? (step["TestData"] as Dictionary<string, object> ?? new Dictionary<string, object>())
        : new Dictionary<string, object>()
                                    };
                                    originalSteps.Add(model);
                                }
                            }
                        }
                    }
                    System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Final original steps count: {originalSteps.Count}");
                    OriginalGrid.ItemsSource = originalSteps;
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Error binding original steps: {ex}");
                    MessageBox.Show($"Error binding original steps: {ex.Message}", "Binding Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }

                try
                {
                    var normalizedSteps = new ObservableCollection<StepModel>();
                    if (tc.ContainsKey("normalized"))
                    {
                        var normalizedData = tc["normalized"];
                        System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Normalized data type: {normalizedData?.GetType().Name}");

                        IEnumerable<Dictionary<string, object>> normalizedList = null;

                        if (normalizedData is JsonElement je)
                        {
                            normalizedList = JsonSerializer.Deserialize<List<Dictionary<string, object>>>(je.GetRawText());
                        }
                        else if (normalizedData is List<Dictionary<string, object>> list)
                        {
                            normalizedList = list;
                        }
                        else if (normalizedData is IEnumerable enumerable)
                        {
                            normalizedList = enumerable.Cast<object>().Select(s => ExtractStepData(s)).Where(s => s != null).ToList();
                        }

                        System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Normalized steps parsed: {normalizedList?.Count() ?? 0}");

                        if (normalizedList != null)
                        {
                            foreach (var step in normalizedList)
                            {
                                if (step != null)
                                {
                                    var model = new StepModel
                                    {
                                        Index = step.ContainsKey("Index") ? step["Index"]?.ToString() ?? "0" : "0",
                                        Step = step.ContainsKey("Step") ? step["Step"]?.ToString() ?? "" : "",
                                        TestDataText = step.ContainsKey("TestDataText") ? step["TestDataText"]?.ToString() ?? "" : "",
                                        TestData = step.ContainsKey("TestData")
         ? (step["TestData"] as Dictionary<string, object> ?? new Dictionary<string, object>())
         : new Dictionary<string, object>()
                                    };
                                    normalizedSteps.Add(model);
                                }
                            }
                        }
                        System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Final normalized steps count: {normalizedSteps.Count}");
                        NormalizedGrid.ItemsSource = normalizedSteps;
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Error binding normalized steps: {ex}");
                    MessageBox.Show($"Error binding normalized steps: {ex.Message}", "Binding Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Error in selection changed: {ex}");
                MessageBox.Show($"Error in TestCaseSelector_SelectionChanged: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private Dictionary<string, object> ExtractStepData(object step)
        {
            try
            {
                if (step is Dictionary<string, object> dict)
                {
                    return dict;
                }
                else if (step is JsonElement je)
                {
                    return JsonSerializer.Deserialize<Dictionary<string, object>>(je.GetRawText());
                }
                else if (step is IDictionary idict)
                {
                    var result = new Dictionary<string, object>();
                    foreach (var key in idict.Keys)
                    {
                        result[key.ToString()] = idict[key];
                    }
                    return result;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[NormalizePreviewWindow] Error extracting step data: {ex}");
                return null;
            }
            return null;
        }

        private void Save_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                // update normalized for each testcase
                foreach (var tc in _data)
                {
                    string id = tc["testcaseid"]?.ToString();
                    if (id == null) continue;

                    // find which steps are currently displayed
                    if (TestCaseSelector.SelectedItem?.ToString() == id)
                    {
                        var items = NormalizedGrid.ItemsSource as ObservableCollection<StepModel>;
                        if (items != null)
                        {
                            tc["normalized"] = items
    .Select(x => new Dictionary<string, object>
    {
        ["Index"] = x.Index,
        ["Step"] = x.Step,
        ["TestDataText"] = x.TestDataText,
        ["TestData"] = x.TestData   // <-- KEEP ORIGINAL TESTDATA
    }).ToList();
                        }
                    }
                }

                UpdatedNormalizedList = _data;
                DialogResult = true;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error saving: {ex.Message}", "Save Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
        }

        public class StepModel : INotifyPropertyChanged
        {
            private string _index;
            private string _step;
            private string _testDataText;
            private Dictionary<string, object> _testData = new();   // <-- NEW

            public string Index
            {
                get => _index;
                set { _index = value; OnPropertyChanged(); }
            }

            public string Step
            {
                get => _step;
                set { _step = value; OnPropertyChanged(); }
            }

            public string TestDataText
            {
                get => _testDataText;
                set { _testDataText = value; OnPropertyChanged(); }
            }

            // 🔥 NEW PROPERTY (to preserve TestData from Gemini)
            public Dictionary<string, object> TestData
            {
                get => _testData;
                set { _testData = value; OnPropertyChanged(); }
            }

            public event PropertyChangedEventHandler PropertyChanged;

            protected void OnPropertyChanged([CallerMemberName] string name = null) =>
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }
    }
}
