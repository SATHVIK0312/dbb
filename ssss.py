using System;
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

            if (_data.Count == 0)
            {
                MessageBox.Show("No test cases to display.", "No Data", MessageBoxButton.OK, MessageBoxImage.Warning);
                Close();
                return;
            }

            // Populate ComboBox
            var ids = _data.Select(x => x["testcaseid"]?.ToString() ?? "Unknown").ToList();
            TestCaseSelector.ItemsSource = ids;
            if (ids.Count > 0) TestCaseSelector.SelectedIndex = 0;
        }

        private void TestCaseSelector_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (TestCaseSelector.SelectedItem is not string selectedId) return;

            var tc = _data.FirstOrDefault(x => x["testcaseid"]?.ToString() == selectedId);
            if (tc == null) return;

            LoadOriginalSteps(tc);
            LoadNormalizedSteps(tc);
        }

        private void LoadOriginalSteps(Dictionary<string, object> tc)
        {
            var steps = new ObservableCollection<StepModel>();

            if (tc.TryGetValue("original", out var originalData) && originalData != null)
            {
                var list = ConvertToStepList(originalData);
                foreach (var item in list)
                {
                    steps.Add(CreateStepModel(item));
                }
            }

            OriginalGrid.ItemsSource = steps;
        }

        private void LoadNormalizedSteps(Dictionary<string, object> tc)
        {
            var steps = new ObservableCollection<StepModel>();

            if (tc.TryGetValue("normalized", out var normalizedData) && normalizedData != null)
            {
                var list = ConvertToStepList(normalizedData);
                foreach (var item in list)
                {
                    steps.Add(CreateStepModel(item));
                }
            }

            NormalizedGrid.ItemsSource = steps;
        }

        private List<Dictionary<string, object>> ConvertToStepList(object data)
        {
            var result = new List<Dictionary<string, object>>();

            try
            {
                if (data is JsonElement je)
                {
                    if (je.ValueKind == JsonValueKind.Array)
                    {
                        return je.Deserialize<List<Dictionary<string, object>>>() ?? new();
                    }
                }
                else if (data is List<Dictionary<string, object>> list)
                {
                    return list;
                }
                else if (data is IEnumerable<object> enumerable)
                {
                    foreach (var item in enumerable)
                    {
                        var dict = ObjectToDictionary(item);
                        if (dict != null) result.Add(dict);
                    }
                    return result;
                }
            }
            catch { /* ignored */ }

            return result;
        }

        private Dictionary<string, object> ObjectToDictionary(object obj)
        {
            if (obj is Dictionary<string, object> dict) return dict;
            if (obj is JsonElement je) return je.Deserialize<Dictionary<string, object>>() ?? new();
            if (obj is System.Collections.IDictionary idict)
            {
                var result = new Dictionary<string, object>();
                foreach (var key in idict.Keys)
                {
                    result[key.ToString()!] = idict[key]!;
                }
                return result;
            }
            return null;
        }

        private StepModel CreateStepModel(Dictionary<string, object> data)
        {
            int index = 1;
            if (data.TryGetValue("Index", out var idxObj) && int.TryParse(idxObj?.ToString(), out var parsed))
                index = parsed;

            return new StepModel
            {
                Index = index.ToString(),
                Step = data.TryGetValue("Step", out var step) ? step?.ToString() ?? "" : "",
                TestDataText = data.TryGetValue("TestDataText", out var tdt) ? tdt?.ToString() ?? "" : "",
                TestData = data.TryGetValue("TestData", out var td) && td is Dictionary<string, object> dict 
                    ? dict 
                    : new Dictionary<string, object>()
            };
        }

        private void Save_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                var selectedId = TestCaseSelector.SelectedItem?.ToString();
                if (string.IsNullOrEmpty(selectedId)) return;

                var tc = _data.FirstOrDefault(x => x["testcaseid"]?.ToString() == selectedId);
                if (tc == null) return;

                var editedSteps = (NormalizedGrid.ItemsSource as ObservableCollection<StepModel>)
                                 ?.Select((s, i) => new Dictionary<string, object>
                                 {
                                     ["Index"] = (i + 1).ToString(),
                                     ["Step"] = s.Step?.Trim() ?? "",
                                     ["TestDataText"] = s.TestDataText?.Trim() ?? "",
                                     ["TestData"] = s.TestData ?? new Dictionary<string, object>()
                                 }).ToList();

                if (editedSteps != null)
                {
                    tc["normalized"] = editedSteps;
                }

                UpdatedNormalizedList = _data;
                DialogResult = true;
                Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Save failed: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }

        // ViewModel for each step
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
                set { _testData = value ?? new(); OnPropertyChanged(); }
            }

            public event PropertyChangedEventHandler? PropertyChanged;
            protected void OnPropertyChanged([CallerMemberName] string name = null) =>
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }
    }
}
