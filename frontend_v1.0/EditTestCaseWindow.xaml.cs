using System.Collections.Generic;
using System.Linq;
using System.Windows;

namespace jpmc_genai
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
                    StepNo = stepsInfo.stepNos[i],              // NEW
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
                .OfType<EditableStep>()
                .ToList();

            // Re-number StepNo final confirmation (in case user reordered steps)
            for (int i = 0; i < EditableSteps.Count; i++)
            {
                EditableSteps[i].StepNo = i + 1;
            }

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

            int nextStepNo = list.Count == 0 ? 1 : list.Max(s => s.StepNo) + 1;

            list.Add(new EditableStep
            {
                StepNo = nextStepNo,
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

            // Re-number after deletion
            for (int i = 0; i < list.Count; i++)
            {
                list[i].Index = i + 1;
                list[i].StepNo = i + 1;   // NEW: Reassign StepNo sequentially
            }

            StepsGrid.ItemsSource = null;
            StepsGrid.ItemsSource = list;
        }
    }

    public class EditableStep
    {
        public int StepNo { get; set; }        // NEW
        public int Index { get; set; }
        public string Step { get; set; }
        public string TestDataText { get; set; }
    }
}
