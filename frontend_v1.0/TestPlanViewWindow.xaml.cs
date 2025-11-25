using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using System.Windows;

namespace JPMCGenAI_v1._0
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
                var data = JsonSerializer.Deserialize<TestPlanResponse>(json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                if (data == null)
                {
                    MessageBox.Show("Invalid test plan format.");
                    return;
                }

                int rowNumber = 1;

                if (data.Pretestid_Steps != null)
                {
                    foreach (var kvp in data.Pretestid_Steps)
                    {
                        string tcid = kvp.Key;
                        int stepNumber = 1;

                        foreach (var step in kvp.Value)
                        {
                            _rows.Add(new TestPlanDisplayRow
                            {
                                RowNumber = rowNumber,
                                TestCaseId = tcid,
                                StepNumber = stepNumber,
                                Step = step.Key,
                                TestData = step.Value,
                                TestCaseType = "Prerequisite"
                            });
                            rowNumber++;
                            stepNumber++;
                        }
                    }
                }

                if (data.Current_Bdd_Steps != null)
                {
                    int stepNumber = 1;
                    foreach (var step in data.Current_Bdd_Steps)
                    {
                        _rows.Add(new TestPlanDisplayRow
                        {
                            RowNumber = rowNumber,
                            TestCaseId = data.Current_TestId,
                            StepNumber = stepNumber,
                            Step = step.Key,
                            TestData = step.Value,
                            TestCaseType = "Actual Test Case"
                        });
                        rowNumber++;
                        stepNumber++;
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error parsing test plan: {ex.Message}");
            }
        }

        private void Close_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }

    public class TestPlanDisplayRow
    {
        public int RowNumber { get; set; }
        public string TestCaseId { get; set; }
        public int StepNumber { get; set; }
        public string Step { get; set; }
        public string TestData { get; set; }
        public string TestCaseType { get; set; }
    }

    // BACKEND RESPONSE MODEL
    public class TestPlanResponse
    {
        public Dictionary<string, Dictionary<string, string>> Pretestid_Steps { get; set; }
        public Dictionary<string, string> Current_Bdd_Steps { get; set; }
        public string Current_TestId { get; set; }
    }
}
