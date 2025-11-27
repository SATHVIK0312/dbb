using System;
using System.Collections.ObjectModel;
using System.Text.Json;
using System.Windows;

namespace jpmc_genai
{
    public partial class TestPlanViewWindow : Window
    {
        private readonly ObservableCollection<TestPlanDisplayRow> _rows = new();

        public TestPlanViewWindow(string json)
        {
            InitializeComponent();
            TestPlanGrid.ItemsSource = _rows;

            try
            {
                var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
                var data = JsonSerializer.Deserialize<TestPlanResponse>(json, options);

                if (data == null)
                {
                    MessageBox.Show("Invalid test plan format.");
                    return;
                }

                int globalRowNumber = 1;

                // Add all prerequisite test cases
                if (data.Pretestid_Steps != null)
                {
                    foreach (var kvp in data.Pretestid_Steps)
                    {
                        string tcId = kvp.Key;
                        int stepNum = 1;

                        foreach (var step in kvp.Value)
                        {
                            _rows.Add(new TestPlanDisplayRow
                            {
                                RowNumber = globalRowNumber++,
                                TestCaseId = tcId,
                                StepNumber = stepNum++,
                                Step = step.Key,
                                TestData = FormatTestData(step.Value),
                                TestCaseType = "Prerequisite"
                            });
                        }
                    }
                }

                // Add the actual current test case
                if (data.Current_Bdd_Steps != null)
                {
                    int stepNum = 1;
                    foreach (var step in data.Current_Bdd_Steps)
                    {
                        _rows.Add(new TestPlanDisplayRow
                        {
                            RowNumber = globalRowNumber++,
                            TestCaseId = data.Current_TestId ?? "Unknown",
                            StepNumber = stepNum++,
                            Step = step.Key,
                            TestData = FormatTestData(step.Value),
                            TestCaseType = "Actual Test Case"
                        });
                    }
                }

                if (globalRowNumber == 1)
                {
                    MessageBox.Show("No steps found in the test plan.");
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error parsing test plan: {ex.Message}\n\n{ex}");
            }
        }

        private string FormatTestData(string data)
        {
            if (string.IsNullOrWhiteSpace(data)) return "-";
            return data.Trim();
        }

        private void Close_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }

    public class TestPlanDisplayRow
    {
        public int RowNumber { get; set; }
        public string TestCaseId { get; set; } = "";
        public int StepNumber { get; set; }
        public string Step { get; set; } = "";
        public string TestData { get; set; } = "";
        public string TestCaseType { get; set; } = "";
    }

    public class TestPlanResponse
    {
        public Dictionary<string, Dictionary<string, string>>? Pretestid_Steps { get; set; }
        public Dictionary<string, string>? Current_Bdd_Steps { get; set; }
        public string? Current_TestId { get; set; }
    }
}
