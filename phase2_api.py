<Page x:Class="JPMCGenAI_v1._0.KnowledgeCenterPage"
      xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
      xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
      Background="#FAF9F6">

    <Grid>
        <Grid.ColumnDefinitions>
            <ColumnDefinition Width="240"/>
            <ColumnDefinition Width="*"/>
        </Grid.ColumnDefinitions>

        <!-- ================= SIDEBAR (COPIED AS-IS) ================= -->
        <Border Grid.Column="0"
                Background="#F8F6F2"
                BorderBrush="#D4AF37"
                BorderThickness="0,0,2,0"
                CornerRadius="0,18,18,0">

            <Grid>
                <Grid.RowDefinitions>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="*"/>
                    <RowDefinition Height="Auto"/>
                </Grid.RowDefinitions>

                <Border Background="#D4AF37" Padding="18">
                    <TextBlock Text="JPMC Flux"
                               Foreground="White"
                               FontSize="22"
                               FontWeight="Bold"
                               HorizontalAlignment="Center"/>
                </Border>

                <StackPanel Grid.Row="1" Margin="20 25 20 10">
                    <Button Content="Project Dashboard"
                            Click="BackToDashboard_Click"
                            Margin="0 0 0 12"/>

                    <Button Content="Manage Test Case"
                            Click="UploadTestCase_Click"
                            Margin="0 0 0 12"/>

                    <Button Content="Smart Executor"
                            Click="AITestExecutor_Click"
                            Margin="0 0 0 12"/>

                    <Button Content="Script Generator"
                            Click="ScriptGenerator_Click"
                            Margin="0 0 0 12"/>

                    <Button Content="Knowledge Center"
                            IsEnabled="False"
                            Margin="0 0 0 12"/>

                    <Button Content="Execution Log"
                            Click="ExecutionLog_Click"
                            Margin="0 0 0 12"/>
                </StackPanel>
            </Grid>
        </Border>

        <!-- ================= MAIN CONTENT ================= -->
        <Grid Grid.Column="1" Margin="25">
            <Grid.RowDefinitions>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="*"/>
            </Grid.RowDefinitions>

            <!-- Header -->
            <StackPanel Grid.Row="0" Margin="0,0,0,20">
                <TextBlock Text="Knowledge Center"
                           FontSize="26"
                           FontWeight="Bold"/>
                <TextBlock Text="Upload documents and preview extracted knowledge"
                           Foreground="#8C8575"/>
            </StackPanel>

            <!-- Upload Section -->
            <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,0,0,20">
                <TextBlock x:Name="SelectedFileText"
                           Text="No file selected"
                           Width="280"
                           VerticalAlignment="Center"/>

                <Button Content="Browse"
                        Width="90"
                        Margin="10,0"
                        Click="BrowseFile_Click"/>

                <Button Content="Analyze"
                        Width="100"
                        Background="#D4AF37"
                        Foreground="White"
                        Click="AnalyzeDocument_Click"/>

                <Button Content="Save"
                        Width="80"
                        Margin="10,0,0,0"
                        Click="SaveDocument_Click"/>
            </StackPanel>

            <!-- Tabs -->
            <TabControl Grid.Row="2">
                <TabItem Header="User Stories">
                    <ListBox x:Name="UserStoriesList"/>
                </TabItem>

                <TabItem Header="Test Cases">
                    <DataGrid x:Name="TestCasesGrid"
                              AutoGenerateColumns="True"/>
                </TabItem>

                <TabItem Header="Software Flow">
                    <ListBox x:Name="FlowList"/>
                </TabItem>
            </TabControl>
        </Grid>
    </Grid>
</Page>
