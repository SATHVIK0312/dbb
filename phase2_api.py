<Page x:Class="JPMCGenAI_v1._0.KnowledgeCenterPage"
      xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
      xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
      Background="#FAF9F6"
      Loaded="Page_Loaded">

    <Grid>
        <Grid.ColumnDefinitions>
            <ColumnDefinition Width="240"/>
            <ColumnDefinition Width="*"/>
        </Grid.ColumnDefinitions>

        <!-- ================= SIDEBAR ================= -->
        <Border Grid.Column="0"
                Background="#F8F6F2"
                BorderBrush="#D4AF37"
                BorderThickness="0,0,2,0"
                CornerRadius="0,18,18,0">

            <Grid>
                <Grid.RowDefinitions>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="*"/>
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
                            Margin="0 0 0 12"
                            Click="BackToDashboard_Click"/>

                    <Button Content="Manage Test Case"
                            Margin="0 0 0 12"
                            Click="UploadTestCase_Click"/>

                    <Button Content="Smart Executor"
                            Margin="0 0 0 12"
                            Click="AITestExecutor_Click"/>

                    <Button Content="Script Generator"
                            Margin="0 0 0 12"
                            Click="ScriptGenerator_Click"/>

                    <Button Content="Knowledge Center"
                            IsEnabled="False"
                            Margin="0 0 0 12"/>

                    <Button Content="Execution Log"
                            Margin="0 0 0 12"
                            Click="ExecutionLog_Click"/>
                </StackPanel>
            </Grid>
        </Border>

        <!-- ================= MAIN CONTENT ================= -->
        <Grid Grid.Column="1" Margin="25">
            <Grid.RowDefinitions>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="*"/>
            </Grid.RowDefinitions>

            <!-- Header -->
            <StackPanel Grid.Row="0" Margin="0,0,0,20">
                <TextBlock Text="Knowledge Center"
                           FontSize="26"
                           FontWeight="Bold"
                           Foreground="#333"/>
                <TextBlock Text="Upload documents and view extracted knowledge"
                           Foreground="#8C8575"
                           Margin="0,5,0,0"/>
            </StackPanel>

            <!-- Upload Section -->
            <Border Grid.Row="1"
                    Background="White"
                    BorderBrush="#D4AF37"
                    BorderThickness="1"
                    CornerRadius="8"
                    Padding="20"
                    Margin="0,0,0,20">
                <StackPanel>
                    <TextBlock Text="Upload New Document"
                               FontSize="16"
                               FontWeight="SemiBold"
                               Foreground="#333"
                               Margin="0,0,0,15"/>
                    
                    <StackPanel Orientation="Horizontal">
                        <TextBlock x:Name="SelectedFileText"
                                   Text="No file selected"
                                   Width="320"
                                   VerticalAlignment="Center"
                                   Foreground="#666"/>

                        <Button Content="Browse"
                                Width="100"
                                Height="32"
                                Margin="15,0"
                                Click="BrowseFile_Click"/>

                        <Button x:Name="AnalyzeButton"
                                Content="Analyze"
                                Width="120"
                                Height="32"
                                Background="#D4AF37"
                                Foreground="White"
                                FontWeight="SemiBold"
                                Click="AnalyzeDocument_Click"/>
                    </StackPanel>
                </StackPanel>
            </Border>

            <!-- Stats Cards -->
            <Grid Grid.Row="2" Margin="0,0,0,20">
                <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="*"/>
                    <ColumnDefinition Width="*"/>
                    <ColumnDefinition Width="*"/>
                </Grid.ColumnDefinitions>

                <!-- User Stories Count -->
                <Border Grid.Column="0"
                        Background="White"
                        BorderBrush="#E2E1DC"
                        BorderThickness="1"
                        CornerRadius="8"
                        Padding="15"
                        Margin="0,0,10,0">
                    <StackPanel>
                        <TextBlock Text="User Stories"
                                   FontSize="14"
                                   Foreground="#8C8575"
                                   Margin="0,0,0,8"/>
                        <TextBlock x:Name="UserStoriesCountText"
                                   Text="0"
                                   FontSize="32"
                                   FontWeight="Bold"
                                   Foreground="#D4AF37"/>
                    </StackPanel>
                </Border>

                <!-- Software Flows Count -->
                <Border Grid.Column="1"
                        Background="White"
                        BorderBrush="#E2E1DC"
                        BorderThickness="1"
                        CornerRadius="8"
                        Padding="15"
                        Margin="5,0">
                    <StackPanel>
                        <TextBlock Text="Software Flows"
                                   FontSize="14"
                                   Foreground="#8C8575"
                                   Margin="0,0,0,8"/>
                        <TextBlock x:Name="SoftwareFlowsCountText"
                                   Text="0"
                                   FontSize="32"
                                   FontWeight="Bold"
                                   Foreground="#D4AF37"/>
                    </StackPanel>
                </Border>

                <!-- Test Cases Count -->
                <Border Grid.Column="2"
                        Background="White"
                        BorderBrush="#E2E1DC"
                        BorderThickness="1"
                        CornerRadius="8"
                        Padding="15"
                        Margin="10,0,0,0">
                    <StackPanel>
                        <TextBlock Text="Test Cases"
                                   FontSize="14"
                                   Foreground="#8C8575"
                                   Margin="0,0,0,8"/>
                        <TextBlock x:Name="TestCasesCountText"
                                   Text="0"
                                   FontSize="32"
                                   FontWeight="Bold"
                                   Foreground="#D4AF37"/>
                    </StackPanel>
                </Border>
            </Grid>

            <!-- TABS -->
            <TabControl Grid.Row="3"
                        Background="White"
                        BorderBrush="#E2E1DC"
                        BorderThickness="1">
                <TabItem Header="User Stories">
                    <DataGrid x:Name="UserStoriesGrid"
                              AutoGenerateColumns="False"
                              IsReadOnly="True"
                              GridLinesVisibility="Horizontal"
                              HeadersVisibility="Column"
                              RowBackground="White"
                              AlternatingRowBackground="#F9F9F9">
                        <DataGrid.Columns>
                            <DataGridTextColumn Header="ID" Binding="{Binding id}" Width="60"/>
                            <DataGridTextColumn Header="Document ID" Binding="{Binding document_id}" Width="100"/>
                            <DataGridTextColumn Header="Story" Binding="{Binding story}" Width="*"/>
                        </DataGrid.Columns>
                    </DataGrid>
                </TabItem>

                <TabItem Header="Software Flows">
                    <DataGrid x:Name="SoftwareFlowsGrid"
                              AutoGenerateColumns="False"
                              IsReadOnly="True"
                              GridLinesVisibility="Horizontal"
                              HeadersVisibility="Column"
                              RowBackground="White"
                              AlternatingRowBackground="#F9F9F9">
                        <DataGrid.Columns>
                            <DataGridTextColumn Header="ID" Binding="{Binding id}" Width="60"/>
                            <DataGridTextColumn Header="Document ID" Binding="{Binding document_id}" Width="100"/>
                            <DataGridTextColumn Header="Step" Binding="{Binding step}" Width="*"/>
                        </DataGrid.Columns>
                    </DataGrid>
                </TabItem>

                <TabItem Header="Test Cases">
                    <DataGrid x:Name="TestCasesGrid"
                              AutoGenerateColumns="False"
                              IsReadOnly="True"
                              GridLinesVisibility="Horizontal"
                              HeadersVisibility="Column"
                              RowBackground="White"
                              AlternatingRowBackground="#F9F9F9">
                        <DataGrid.Columns>
                            <DataGridTextColumn Header="ID" Binding="{Binding id}" Width="50"/>
                            <DataGridTextColumn Header="Test Case ID" Binding="{Binding test_case_id}" Width="100"/>
                            <DataGridTextColumn Header="Description" Binding="{Binding description}" Width="250"/>
                            <DataGridTextColumn Header="Tags" Binding="{Binding tags}" Width="100"/>
                            <DataGridTextColumn Header="Arguments" Binding="{Binding arguments}" Width="*"/>
                        </DataGrid.Columns>
                    </DataGrid>
                </TabItem>
            </TabControl>
        </Grid>
    </Grid>
</Page>
