using System.Collections.Generic;
using System.Linq;
using System.Windows;

namespace JPMCGenAI_v1._0
{
    public partial class TestCaseDetailWindow_Local : Window
    {
        private readonly UploadTestCasePage.GroupedTestCase _tc;

        public TestCaseDetailWindow_Local(UploadTestCasePage.GroupedTestCase tc)
        {
            InitializeComponent();
            _tc = tc;

            TitleLbl.Text = $"[Staged] {_tc.TestCaseId}";
            TcIdText.Text = _tc.TestCaseId;
            DescText.Text = _tc.Description;
            TagsText.Text = string.Join(", ", _tc.Tags);
            PrereqText.Text = _tc.PreReqDesc ?? "Draft (staged)";

            StepsDataGrid.ItemsSource = _tc.Steps.Select((s, i) => new StepView
            {
                Index = i + 1,
                Description = s.Step,
                TestDataText = string.IsNullOrWhiteSpace(s.Argument) ? "—" : s.Argument
            }).ToList();
        }

        private class StepView
        {
            public int Index { get; set; }
            public string Description { get; set; }
            public string TestDataText { get; set; }
        }

        private void Close_Click(object sender, RoutedEventArgs e) => Close();
    }
}
