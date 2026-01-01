<Page x:Class="JPMCGenAI_v1._0.KnowledgeCenterPage"
      xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
      xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
      Background="#FAF9F6"
      Title="KnowledgeCenterPage">

    <Grid Margin="25">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <!-- HEADER -->
        <StackPanel Grid.Row="0" Margin="0,0,0,20">
            <TextBlock Text="Knowledge Center"
                       FontSize="26"
                       FontWeight="Bold"
                       Foreground="#333"/>

            <TextBlock Text="Upload documents to extract user stories, test cases, and flows"
                       FontSize="13"
                       Foreground="#8C8575"/>
        </StackPanel>

        <!-- UPLOAD SECTION -->
        <Border Grid.Row="1"
                Background="White"
                CornerRadius="12"
                Padding="16"
                Margin="0,0,0,20"
                BorderBrush="#E2E1DC"
                BorderThickness="1">

            <StackPanel Orientation="Horizontal" VerticalAlignment="Center">

                <TextBlock Text="📄"
                           FontSize="18"
                           Margin="0,0,10,0"/>

                <TextBlock x:Name="SelectedFileText"
                           Text="No file selected"
                           VerticalAlignment="Center"
                           Foreground="#555"
                           Width="280"/>

                <Button Content="Browse"
                        Width="90"
                        Margin="10,0"
                        Click="BrowseFile_Click"/>

                <Button Content="Analyze"
                        Width="100"
                        Background="#D4AF37"
                        Foreground="White"
                        FontWeight="SemiBold"
                        Click="AnalyzeDocument_Click"/>

                <Button Content="Save"
                        Width="80"
                        Margin="10,0,0,0"
                        Click="SaveDocument_Click"/>
            </StackPanel>
        </Border>

        <!-- PREVIEW TABS -->
        <TabControl Grid.Row="2">

            <!-- USER STORIES -->
            <TabItem Header="User Stories">
                <ListBox x:Name="UserStoriesList"
                         Margin="10">
                    <ListBox.ItemTemplate>
                        <DataTemplate>
                            <Border Padding="10"
                                    Margin="0,0,0,10"
                                    Background="White"
                                    CornerRadius="8"
                                    BorderBrush="#E2E1DC"
                                    BorderThickness="1">
                                <TextBlock Text="{Binding}"
                                           TextWrapping="Wrap"/>
                            </Border>
                        </DataTemplate>
                    </ListBox.ItemTemplate>
                </ListBox>
            </TabItem>

            <!-- TEST CASES -->
            <TabItem Header="Test Cases">
                <DataGrid x:Name="TestCasesGrid"
                          AutoGenerateColumns="False"
                          Margin="10">
                    <DataGrid.Columns>
                        <DataGridTextColumn Header="ID" Binding="{Binding TestCaseId}" Width="100"/>
                        <DataGridTextColumn Header="Description" Binding="{Binding Description}" Width="*"/>
                    </DataGrid.Columns>
                </DataGrid>
            </TabItem>

            <!-- SOFTWARE FLOW -->
            <TabItem Header="Software Flow">
                <ListBox x:Name="FlowList"
                         Margin="10">
                    <ListBox.ItemTemplate>
                        <DataTemplate>
                            <StackPanel Orientation="Horizontal">
                                <TextBlock Text="➜ "
                                           FontWeight="Bold"/>
                                <TextBlock Text="{Binding}"
                                           TextWrapping="Wrap"/>
                            </StackPanel>
                        </DataTemplate>
                    </ListBox.ItemTemplate>
                </ListBox>
            </TabItem>

        </TabControl>
    </Grid>
</Page>
