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
                    StepNo = stepsInfo.stepNos.ElementAtOrDefault(i),
                    Index = i + 1,
                    Step = stepsInfo.steps[i],
                    TestDataText = stepsInfo.args.ElementAtOrDefault(i) ?? ""
                });
            }

            StepsGrid.ItemsSource = list;
        }

        private void Save_Click(object sender, RoutedEventArgs e)
        {
            var list = StepsGrid.Items.Cast<EditableStep>().ToList();

            for (int i = 0; i < list.Count; i++)
            {
                list[i].StepNo = i + 1;
                list[i].Index = i + 1;
            }

            EditableSteps = list;
            DialogResult = true;
            Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void AddStep_Click(object sender, RoutedEventArgs e)
        {
            var list = StepsGrid.Items.Cast<EditableStep>().ToList();

            list.Add(new EditableStep
            {
                StepNo = list.Count + 1,
                Index = list.Count + 1,
                Step = "",
                TestDataText = ""
            });

            StepsGrid.ItemsSource = null;
            StepsGrid.ItemsSource = list;
        }

        private void DeleteStep_Click(object sender, RoutedEventArgs e)
        {
            if (StepsGrid.SelectedItem is not EditableStep selected)
            {
                MessageBox.Show("Select a step to delete.");
                return;
            }

            var list = StepsGrid.Items.Cast<EditableStep>().ToList();
            list.Remove(selected);

            for (int i = 0; i < list.Count; i++)
            {
                list[i].StepNo = i + 1;
                list[i].Index = i + 1;
            }

            StepsGrid.ItemsSource = null;
            StepsGrid.ItemsSource = list;
        }
    }

    public class EditableStep
    {
        public int StepNo { get; set; }
        public int Index { get; set; }
        public string Step { get; set; }
        public string TestDataText { get; set; }
    }
}
