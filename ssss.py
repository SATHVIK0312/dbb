using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
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

            Debug.WriteLine($"[DEBUG] Received {_data.Count} test cases in preview window");

            if (_data.Count == 0)
            {
                MessageBox.Show("No test cases received!", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                Close();
                return;
            }

            // Show what we actually received
            foreach (var tc in _data)
            {
                var id = tc.TryGetValue("testcaseid", out var tid) ? tid?.ToString() : "null";
                var hasOriginal = tc.ContainsKey("original");
                var hasNormalized = tc.ContainsKey("normalized");
                Debug.WriteLine($"[DEBUG] TestCase: {id} | Has Original: {hasOriginal} | Has Normalized: {hasNormalized}");
            }

            TestCaseSelector.ItemsSource = _data.Select(x => x["testcaseid"]?.ToString() ?? "Unknown").ToList();
            TestCaseSelector.SelectedIndex = 0;
        }

        private void TestCaseSelector_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (TestCaseSelector.SelectedItem is not string selectedId) return;

            var tc = _data.FirstOrDefault(x => x["testcaseid"]?.ToString() == selectedId);
            if (tc == null)
            {
                Debug.WriteLine($"[ERROR] Test case {selectedId} not found!");
                return;
            }

            Debug.WriteLine($"[INFO] Loading data for {selectedId}");

            // Clear grids first
            OriginalGrid.ItemsSource = null;
            NormalizedGrid.ItemsSource = null;

            LoadSteps(tc, "original", OriginalGrid);
            LoadSteps(tc, "normalized", NormalizedGrid);
        }

        private void LoadSteps(Dictionary<string, object> tc, string key, DataGrid grid)
        {
            var collection = new ObservableCollection<StepModel>();

            if (!tc.TryGetValue(key, out var rawData) || rawData == null)
            {
                Debug.WriteLine($"[WARN] No '{key}' field found in test case");
                grid.ItemsSource = collection;
                return;
            }

            Debug.WriteLine($"[DEBUG] Raw '{key}' type: {rawData.GetType().Name}");

            List<Dictionary<string, object>> steps = rawData switch
            {
                JsonElement je when je.ValueKind == JsonValueKind.Array =>
                    je.Deserialize<List<Dictionary<string, object>>>() ?? new(),

                List<Dictionary<string, object>> list => list,

                IEnumerable<object> enumerable => enumerable
                    .Select(item => ConvertToDict(item))
                    .Where(d => d != null)
                    .ToList()!,

                _ => new List<Dictionary<string, object>>()
            };

            Debug.WriteLine($"[INFO] Parsed {steps.Count} steps for '{key}'");

            int index = 1;
            foreach (var step in steps)
            {
                collection.Add(new StepModel
                {
                    Index = step.TryGetValue("Index", out var i) ? i?.ToString() ?? index.ToString() : index.ToString(),
                    Step = step.TryGetValue("Step", out var s) ? (s?.ToString() ?? "") : "",
                    TestDataText = step.TryGetValue("TestDataText", out var t) ? (t?.ToString() ?? "") : "",
                    TestData = step.TryGetValue("TestData", out var td) && td is Dictionary<string, object> d ? d : new()
                });
                index++;
            }

            grid.ItemsSource = collection;
            Debug.WriteLine($"[SUCCESS] Loaded {collection.Count} steps into {grid.Name}");
        }

        private Dictionary<string, object>? ConvertToDict(object obj)
        {
            return obj switch
            {
                Dictionary<string, object> d => d,
                JsonElement je => je.Deserialize<Dictionary<string, object>>() ?? new(),
                System.Collections.IDictionary idict => idict.Keys.Cast<object>()
                    .ToDictionary(k => k.ToString()!, k => idict[k]!),
                _ => null
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

                var currentSteps = NormalizedGrid.ItemsSource as ObservableCollection<StepModel>;
                if (currentSteps != null)
                {
                    var updated = currentSteps.Select((s, i) => new Dictionary<string, object>
                    {
                        ["Index"] = (i + 1).ToString(),
                        ["Step"] = s.Step?.Trim() ?? "",
                        ["TestDataText"] = s.TestDataText?.Trim() ?? "",
                        ["TestData"] = s.TestData ?? new Dictionary<string, object>()
                    }).ToList();

                    tc["normalized"] = updated;
                    Debug.WriteLine($"[SAVE] Updated {updated.Count} normalized steps for {selectedId}");
                }

                UpdatedNormalizedList = _data;
                DialogResult = true;
                Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Save failed: {ex.Message}\n\n{ex.StackTrace}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }

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
