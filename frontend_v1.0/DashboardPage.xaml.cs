using System;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using jpmc_genai.Services;

namespace jpmc_genai
{
    public partial class DashboardPage : Page
    {
        private readonly string _projectId;

        public DashboardPage(string projectId)
        {
            InitializeComponent();
            _projectId = projectId;

            // Update sidebar project info
            if (FindName("Sidebar") is FluxSidebar sidebar)
            {
                var project = Session.CurrentUser?.projects?.FirstOrDefault(p => p.projectid == projectId);
                sidebar.UpdateProjectInfo(project?.title ?? "Unknown Project", $"ID: {projectId}");
            }

            _ = LoadSummaryAsync();
        }

        public ICommand NavigateCommand => new RelayCommand(param =>
        {
            switch (param?.ToString())
            {
                case "UploadTestCase":
                    NavigationService?.Navigate(new UploadTestCasePage());
                    break;
                case "AITestExecutor":
                    NavigationService?.Navigate(new AITestExecutorPage(_projectId));
                    break;
                case "ScriptGenerator":
                    NavigationService?.Navigate(new ScriptGeneratorPage());
                    break;
                case "ExecutionLog":
                    NavigationService?.Navigate(new ExecutionLogPage());
                    break;
                case "ChangeProject":
                    NavigationService?.Navigate(new ProjectPage());
                    break;
            }
        });

        private async Task LoadSummaryAsync()
        {
            try
            {
                using var client = new ApiClient();
                client.SetBearer(Session.Token);
                var resp = await client.GetAsync($"projects/{_projectId}/summary");

                if (resp.IsSuccessStatusCode)
                {
                    var json = await resp.Content.ReadAsStringAsync();
                    var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
                    var summary = JsonSerializer.Deserialize<ProjectSummary>(json, options);

                    if (summary != null)
                    {
                        UsersCountTextBlock.Text = summary.users_count.ToString("N0");
                        TestCasesCountTextBlock.Text = summary.testcases_count.ToString("N0");
                        TotalExecutionsTextBlock.Text = summary.total_executions.ToString("N0");
                        SuccessfulExecutionsTextBlock.Text = $"{summary.successful_executions} Passed";
                        FailedExecutionsTextBlock.Text = $"{summary.failed_executions} Failed";
                    }
                }
                else
                {
                    SetPlaceholder();
                }
            }
            catch
            {
                SetPlaceholder();
            }
        }

        private void SetPlaceholder()
        {
            UsersCountTextBlock.Text = "—";
            TestCasesCountTextBlock.Text = "—";
            TotalExecutionsTextBlock.Text = "—";
            SuccessfulExecutionsTextBlock.Text = "—";
            FailedExecutionsTextBlock.Text = "—";
        }

        private class ProjectSummary
        {
            public int users_count { get; set; }
            public int testcases_count { get; set; }
            public int total_executions { get; set; }
            public int successful_executions { get; set; }
            public int failed_executions { get; set; }
        }
    }

    // Simple RelayCommand (add this once in your project)
    public class RelayCommand : ICommand
    {
        private readonly Action<object> _execute;
        public event EventHandler CanExecuteChanged;
        public RelayCommand(Action<object> execute) => _execute = execute;
        public bool CanExecute(object parameter) => true;
        public void Execute(object parameter) => _execute(parameter);
    }
}
