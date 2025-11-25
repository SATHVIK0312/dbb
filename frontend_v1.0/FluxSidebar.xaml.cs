using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace JPMXGenAI_v1._0
{
    public partial class FluxSidebar : UserControl
    {
        public static readonly DependencyProperty NavigateCommandProperty =
            DependencyProperty.Register("NavigateCommand", typeof(ICommand), typeof(FluxSidebar), new PropertyMetadata(null));

        public ICommand NavigateCommand
        {
            get => (ICommand)GetValue(NavigateCommandProperty);
            set => SetValue(NavigateCommandProperty, value);
        }

        public FluxSidebar()
        {
            InitializeComponent();
            DataContext = this; // So commands work
        }

        public void UpdateProjectInfo(string title, string details)
        {
            ProjectTitleTextBlock.Text = title ?? "No Project";
            ProjectDetailsTextBlock.Text = details ?? "—";
        }
    }
}
