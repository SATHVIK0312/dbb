using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;

namespace jpmc_genai
{
    public partial class NormalizePreviewWindow : Window
    {
        private List<Dictionary<string, object>> _data;
        public List<Dictionary<string, object>> UpdatedNormalizedList { get; private set; }

        public NormalizePreviewWindow(List<Dictionary<string, object>> normalizedData)
        {
            InitializeComponent();
            _data = normalizedData ?? new List<Dictionary<string, object>>();

            if (_data.Count > 0)
            {
                var ids = _data.Select(x => x["testcaseid"]?.ToString()).Where(id => id != null).ToList();
                TestCaseSelector.ItemsSource = ids;
                if (ids.Count > 0)
                    TestCaseSelector.SelectedIndex = 0;
            }
            else
            {
                MessageBox.Show("No test cases to display.", "Empty Data", MessageBoxButton.OK, MessageBoxImage.Warning);
                Close();
            }
        }

        private void TestCaseSelector_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (TestCaseSelector.SelectedItem is not string selectedId) return;

            var tc = _data.FirstOrDefault(x => x["testcaseid"]?.ToString() == selectedId);
            if (tc == null) return;

            var originalSteps = new ObservableCollection<StepModel>();
            var normalizedSteps = new ObservableCollection<StepModel>();

            // Load Original Steps
            if (tc.TryGetValue("original", out var originalObj) && originalObj != null)
            {
                var steps = ConvertToStepList(originalObj);
                LoadStepsIntoGrid(steps, originalSteps);
            }

            // Load Normalized Steps
            if (tc.TryGetValue("normalized", out var normalizedObj) && normalizedObj != null)
            {
                var steps = ConvertToStepList(normalizedObj);
                LoadStepsIntoGrid(steps, normalizedSteps);
            }

            OriginalGrid.ItemsSource = originalSteps;
            NormalizedGrid.ItemsSource = normalizedSteps;
        }

        private IEnumerable<Dictionary<string, object>> ConvertToStepList(object data)
        {
            if (data is JsonElement je)
            {
                try
                {
                    return JsonSerializer.Deserialize<List<Dictionary<string, object>>>(je.GetRawText()) ?? new();
                }
                catch
                {
                    return new List<Dictionary<string, object>>();
                }
            }

            if (data is List<Dictionary<string, object>> list)
                return list;

            if (data is IEnumerable enumerable)
            {
                var result = new List<Dictionary<string, object>>();
                foreach (var item in enumerable)
                {
                    var dict = ExtractStepData(item);
                    if (dict != null)
                        result.Add(dict);
                }
                return result;
            }

            return new List<Dictionary<string, object>>();
        }

        private Dictionary<string, object> ExtractStepData(object step)
        {
            try
            {
                if (step is Dictionary<string, object> dict) return dict;
                if (step is JsonElement je)
                    return JsonSerializer.Deserialize<Dictionary<string, object>>(je.GetRawText());
                if (step is IDictionary idict)
                {
                    var result = new Dictionary<string, object>();
                    foreach (var key in idict.Keys)
                    {
                        if (key != null)
                            result[key.ToString()] = idict[key];
                    }
                    return result;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[ExtractStepData] Error: {ex.Message}");
            }
            return null;
        }

        private void LoadStepsIntoGrid(IEnumerable<Dictionary<string, object>> steps, ObservableCollection<StepModel> collection)
        {
            collection.Clear();
            if (steps == null) return;

            int index = 1;
            foreach (var step in steps)
            {
                if (step == null) continue;

                var model = new StepModel
                {
                    Index = index.ToString(),
                    Step = step.TryGetValue("Step", out var s) ? (s?.ToString() ?? "").Trim() : "",
                    TestDataText = step.TryGetValue("TestDataText", out var t) ? (t?.ToString() ?? "").Trim() : "",
                    TestData = step.TryGetValue("TestData", out var td) && td is Dictionary<string, object> dict
                        ? dict
                        : new Dictionary<string, object>()
                };

                collection.Add(model);
                index++;
            }
        }

        private void Save_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                string selectedId = TestCaseSelector.SelectedItem?.ToString();
                if (string.IsNullOrEmpty(selectedId)) return;

                var tc = _data.FirstOrDefault(x => x["testcaseid"]?.ToString() == selectedId);
                if (tc == null) return;

                var items = NormalizedGrid.ItemsSource as ObservableCollection<StepModel>;
                if (items != null && items.Count > 0)
                {
                    var updatedSteps = items.Select((x, idx) => new Dictionary<string, object>
                    {
                        ["Index"] = (idx + 1).ToString(),
                        ["Step"] = x.Step?.Trim() ?? "",
                        ["TestDataText"] = x.TestDataText?.Trim() ?? "",
                        ["TestData"] = x.TestData ?? new Dictionary<string, object>()
                    }).ToList();

                    tc["normalized"] = updatedSteps;
                }

                UpdatedNormalizedList = _data;
                DialogResult = true;
                Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error saving changes:\n{ex.Message}", "Save Failed", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }

        // ──────────────────────────────────────────────
        // StepModel with INotifyPropertyChanged
        // ──────────────────────────────────────────────
        public class StepModel : INotifyPropertyChanged
        {
            private string _index = "";
            private string _step = "";
            private string _testDataText = "";
            private Dictionary<string, object> _testData = new();

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

            public Dictionary<string, object> TestData
            {
                get => _testData;
                set { _testData = value ?? new Dictionary<string, object>(); OnPropertyChanged(); }
            }

            public event PropertyChangedEventHandler PropertyChanged;

            protected void OnPropertyChanged([CallerMemberName] string name = null)
                => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }
    }
}
