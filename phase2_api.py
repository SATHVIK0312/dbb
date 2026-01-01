<Button Content="Knowledge Center"
        Style="{StaticResource SidebarButtonTheme}"
        Click="KnowledgeCenter_Click"
        Margin="0 0 0 12"/>


private void KnowledgeCenter_Click(object sender, RoutedEventArgs e)
{
    NavigationService?.Navigate(new KnowledgeCenterPage());
}
