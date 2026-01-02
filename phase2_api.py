<Button x:Name="AnalyzeButton"
        Content="Analyze"
        Width="100"
        Background="#D4AF37"
        Foreground="White"
        Click="AnalyzeDocument_Click"/>



<!-- RAW API PREVIEW -->
<Border Grid.Row="2"
        Background="White"
        BorderBrush="#E2E1DC"
        BorderThickness="1"
        CornerRadius="8"
        Padding="10"
        Margin="0,0,0,10">

    <ScrollViewer Height="140">
        <TextBlock x:Name="PreviewTextBlock"
                   Text="Preview will appear here after analysis..."
                   TextWrapping="Wrap"
                   Foreground="#444"
                   FontFamily="Consolas"
                   FontSize="12"/>
    </ScrollViewer>
</Border>




private async void AnalyzeDocument_Click(object sender, RoutedEventArgs e)
{
    if (string.IsNullOrEmpty(_selectedFilePath))
    {
        MessageBox.Show("Please select a document first.",
            "Validation",
            MessageBoxButton.OK,
            MessageBoxImage.Warning);
        return;
    }

    try
    {
        // ---------------- UI: Analyzing state ----------------
        AnalyzeButton.IsEnabled = false;
        AnalyzeButton.Content = "Analyzing...";
        PreviewTextBlock.Text = "Analyzing document, please wait...";

        // 🔑 Force UI to update BEFORE async call
        await Dispatcher.InvokeAsync(() => { }, System.Windows.Threading.DispatcherPriority.Background);

        using var client = new ApiClient();
        client.SetBearer(Session.Token);

        // ---------------- API CALL ----------------
        var response = await client.PostFileAsync(
            "analyze-document",
            _selectedFilePath
        );

        var json = await response.Content.ReadAsStringAsync();

        // ---------------- PREVIEW RAW RESPONSE ----------------
        PreviewTextBlock.Text = json;

        if (!response.IsSuccessStatusCode)
        {
            MessageBox.Show(
                $"Analyze failed: {response.StatusCode}",
                "API Error",
                MessageBoxButton.OK,
                MessageBoxImage.Error
            );
            return;
        }

        // ---------------- DESERIALIZE ----------------
        _lastAnalyzeResult = JsonSerializer.Deserialize<AnalyzeResult>(
            json,
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
        );

        if (_lastAnalyzeResult == null)
        {
            PreviewTextBlock.Text = "Unable to parse API response.";
            return;
        }

        // ---------------- UPDATE TABS ----------------
        UserStoriesList.ItemsSource = null;
        FlowList.ItemsSource = null;
        TestCasesGrid.ItemsSource = null;

        UserStoriesList.ItemsSource = _lastAnalyzeResult.user_stories ?? new();
        FlowList.ItemsSource = _lastAnalyzeResult.software_flow ?? new();
        TestCasesGrid.ItemsSource = _lastAnalyzeResult.test_cases ?? new();
    }
    catch (Exception ex)
    {
        PreviewTextBlock.Text = $"Error:\n{ex}";
        MessageBox.Show(
            ex.Message,
            "Unexpected Error",
            MessageBoxButton.OK,
            MessageBoxImage.Error
        );
    }
    finally
    {
        // ---------------- UI: Reset ----------------
        AnalyzeButton.IsEnabled = true;
        AnalyzeButton.Content = "Analyze";
    }
}
