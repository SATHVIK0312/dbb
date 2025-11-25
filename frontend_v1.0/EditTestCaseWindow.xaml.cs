using System.Collections.Generic;
using System.Linq;
using System.Windows;

namespace JPMCGenAI_v1._0
{
    public partial class EditTestCaseWindow : Window
    {
        public List<EditableStep> EditableSteps { get; private set; } = new();

        public EditTestCaseWindow(string testcaseId, TestStepInfo stepsInfo)
        {
            InitializeComponent();
            IdLbl.Text = $"Editing: {testcaseId}";

            var list = new List<EditableStep>();
            for (int i = 0; i < stepsInfo.steps.Count; i++)
            {
                list.Add(new EditableStep
                {
                    Index = i + 1,
                    Step = stepsInfo.steps[i] ?? "",
                    TestDataText = (i < stepsInfo.args.Count ? stepsInfo.args[i] : "") ?? ""
                });
            }

            StepsGrid.ItemsSource = list;
        }

        private void Save_Click(object sender, RoutedEventArgs e)
        {
            EditableSteps = StepsGrid.Items
                .OfType<EditableStep>()   // this filters out NamedObject
                .ToList();

            DialogResult = true;
            Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        // ============================================================
        // ADD STEP
        // ============================================================
        private void AddStep_Click(object sender, RoutedEventArgs e)
        {
            var list = StepsGrid.Items.Cast<EditableStep>().ToList();

            list.Add(new EditableStep
            {
                Index = list.Count + 1,
                Step = "",
                TestDataText = ""
            });

            StepsGrid.ItemsSource = null;
            StepsGrid.ItemsSource = list;
        }

        // ============================================================
        // DELETE STEP
        // ============================================================
        private void DeleteStep_Click(object sender, RoutedEventArgs e)
        {
            if (StepsGrid.SelectedItem is not EditableStep selected)
            {
                MessageBox.Show("Please select a step to delete.");
                return;
            }

            var list = StepsGrid.Items.Cast<EditableStep>().ToList();
            list.Remove(selected);

            // Re-number indexes
            for (int i = 0; i < list.Count; i++)
                list[i].Index = i + 1;

            StepsGrid.ItemsSource = null;
            StepsGrid.ItemsSource = list;
        }
    }
}
