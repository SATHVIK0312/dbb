using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace jpmc_genai
{
    /// <summary>
    /// Reusable JPMC Flux Sidebar for JPMXGenAI_v1.0
    /// </summary>
    public partial class FluxSidebar : UserControl
    {
        // Dependency Property to receive navigation command from parent page
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
            InitializeComponent(); // This now works — because class is partial and linked to XAML
        }
    }

    // Simple, clean RelayCommand — add once in project
    public class RelayCommand : ICommand
    {
        private readonly Action<object> _execute;
        public event EventHandler CanExecuteChanged;

        public RelayCommand(Action<object> execute)
        {
            _execute = execute ?? throw new ArgumentNullException(nameof(execute));
        }

        public bool CanExecute(object parameter) => true;
        public void Execute(object parameter) => _execute(parameter);
    }
}
