using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace jpmc_genai
{
    public partial class FluxSidebar : UserControl
    {
        public static readonly DependencyProperty NavigateCommandProperty =
            DependencyProperty.Register(
                nameof(NavigateCommand),
                typeof(ICommand),
                typeof(FluxSidebar),
                new PropertyMetadata(null));

        public ICommand NavigateCommand
        {
            get => (ICommand)GetValue(NavigateCommandProperty);
            set => SetValue(NavigateCommandProperty, value);
        }

        public FluxSidebar()
        {
            InitializeComponent();
            DataContext = this; // Required for Command binding in XAML
        }

        /// <summary>
        /// Updates the project info displayed in the sidebar footer
        /// </summary>
        public void UpdateProjectInfo(string title, string details)
        {
            ProjectTitleTextBlock.Text = string.IsNullOrWhiteSpace(title) ? "No Project Selected" : title;
            ProjectDetailsTextBlock.Text = string.IsNullOrWhiteSpace(details) ? "—" : details;
        }

        // ─────────────────────────────────────────────────────────────────────
        // Centralized Navigation Command – used by all sidebar buttons
        // ─────────────────────────────────────────────────────────────────────
        public ICommand SidebarNavigateCommand => new RelayCommand(param =>
        {
            if (param is not string target) return;

            Page destinationPage = target switch
            {
                "Dashboard"         => new DashboardPage(GetCurrentProjectId()),
                "UploadTestCase"    => new UploadTestCasePage(),
                "AITestExecutor"    => new AITestExecutorPage(GetCurrentProjectId()),
                "ScriptGenerator"   => new ScriptGeneratorPage(),
                "ExecutionLog"      => new ExecutionLogPage(),
                "ChangeProject"     => new ProjectPage(),           // Takes user back to project selection
                _                   => null
            };

            if (destinationPage != null)
            {
                // Works whether the sidebar is inside a Page or a Frame in MainWindow
                if (this.TryFindParent<Page>() is Page currentPage && currentPage.NavigationService != null)
                {
                    currentPage.NavigationService.Navigate(destinationPage);
                }
                else if (Application.Current.MainWindow?.FindName("MainFrame") is Frame frame)
                {
                    frame.Navigate(destinationPage);
                }
            }
        });

        /// <summary>
        /// Helper to get current project ID from the active page (Dashboard or AITestExecutor)
        /// </summary>
        private string GetCurrentProjectId()
        {
            if (this.TryFindParent<DashboardPage>() is DashboardPage dashboard && 
                dashboard.GetType().GetField("_projectId", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)?
                        .GetValue(dashboard) is string id && !string.IsNullOrEmpty(id))
            {
                return id;
            }

            if (this.TryFindParent<AITestExecutorPage>() is AITestExecutorPage executor && 
                executor.GetType().GetField("_projectId", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)?
                        .GetValue(executor) is string execId && !string.IsNullOrEmpty(execId))
            {
                return execId;
            }

            return string.Empty;
        }
    }

    // ─────────────────────────────────────────────────────────────────────
    // Simple RelayCommand (add only once in your project – safe to duplicate)
    // ─────────────────────────────────────────────────────────────────────
    public class RelayCommand : ICommand
    {
        private readonly Action<object> _execute;
        public event EventHandler CanExecuteChanged;

        public RelayCommand(Action<object> execute)
        {
            _execute = execute;
        }

        public bool CanExecute(object parameter) => true;
        public void Execute(object parameter) => _execute?.Invoke(parameter);
    }

    // ─────────────────────────────────────────────────────────────────────
    // Visual Tree Helper Extension (add once in project)
    // ─────────────────────────────────────────────────────────────────────
    public static class VisualTreeExtensions
    {
        public static T TryFindParent<T>(this DependencyObject child) where T : DependencyObject
        {
            DependencyObject parentObject = VisualTreeHelper.GetParent(child);

            while (parentObject != null && parentObject is not T)
            {
                parentObject = VisualTreeHelper.GetParent(parentObject);
            }

            return parentObject as T;
        }
    }
}
