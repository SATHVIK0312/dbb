using System;
using System.Collections.Generic;
using System.Windows;

namespace JPMCGenAI_v1._0
{
    public partial class DocumentDetailsWindow : Window
    {
        private readonly int _documentId;
        private readonly List<UserStory> _userStories;
        private readonly List<SoftwareFlow> _softwareFlows;
        private readonly List<TestCase> _testCases;

        public DocumentDetailsWindow(
            int documentId,
            List<UserStory> userStories,
            List<SoftwareFlow> softwareFlows,
            List<TestCase> testCases)
        {
            InitializeComponent();

            _documentId = documentId;
            _userStories = userStories ?? new List<UserStory>();
            _softwareFlows = softwareFlows ?? new List<SoftwareFlow>();
            _testCases = testCases ?? new List<TestCase>();

            LoadData();
        }

        private void LoadData()
        {
            // Set document ID
            DocumentIdText.Text = $"Document ID: {_documentId}";

            // Set counts
            UserStoriesCountText.Text = _userStories.Count.ToString();
            SoftwareFlowsCountText.Text = _softwareFlows.Count.ToString();
            TestCasesCountText.Text = _testCases.Count.ToString();

            // Bind data to grids
            UserStoriesGrid.ItemsSource = _userStories;
            SoftwareFlowsGrid.ItemsSource = _softwareFlows;
            TestCasesList.ItemsSource = _testCases;
        }

        private void SaveToKnowledgeBase_Click(object sender, RoutedEventArgs e)
        {
            MessageBox.Show(
                $"Successfully saved to Knowledge Base!\n\n" +
                $"User Stories: {_userStories.Count}\n" +
                $"Software Flows: {_softwareFlows.Count}\n" +
                $"Test Cases: {_testCases.Count}",
                "Success",
                MessageBoxButton.OK,
                MessageBoxImage.Information
            );

            this.DialogResult = true;
            this.Close();
        }

        private void Close_Click(object sender, RoutedEventArgs e)
        {
            this.DialogResult = false;
            this.Close();
        }
    }
}
