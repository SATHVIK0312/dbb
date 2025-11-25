using System.Windows;

namespace JPMCGenAI_v1._0
{
    public partial class ExecutionLogViewWindow : Window
    {
        public ExecutionLogViewWindow(ExecutionHistoryModel model)
        {
            InitializeComponent();

            // Column2 contains the logs
            LogsTextBox.Text = model.Column2 ?? "No logs available.";
        }
    }
}
