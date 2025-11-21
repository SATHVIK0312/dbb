using System.Windows;

namespace JPMCGenAI_v1._0
{
    public partial class LoginWindow : Window
    {
        public LoginWindow()
        {
            InitializeComponent();
            MainFrame.Navigate(new LoginPage());
        }
    }

}
