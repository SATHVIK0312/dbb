<Window x:Class="JPMCGenAI_v1._0.DocumentDetailsWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Document Analysis Results"
        Height="700"
        Width="1100"
        WindowStartupLocation="CenterScreen"
        Background="#FAF9F6">

    <Grid Margin="25">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>

        <!-- Header -->
        <StackPanel Grid.Row="0" Margin="0,0,0,20">
            <TextBlock Text="Document Analysis Complete"
                       FontSize="24"
                       FontWeight="Bold"
                       Foreground="#333"/>
            <TextBlock x:Name="DocumentIdText"
                       Text="Document ID: --"
                       FontSize="14"
                       Foreground="#8C8575"
                       Margin="0,5,0,0"/>
        </StackPanel>

        <!-- Stats Cards -->
        <Grid Grid.Row="1" Margin="0,0,0,20">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="*"/>
                <ColumnDefinition Width="*"/>
                <ColumnDefinition Width="*"/>
            </Grid.ColumnDefinitions>

            <!-- User Stories Count -->
            <Border Grid.Column="0"
                    Background="White"
                    BorderBrush="#D4AF37"
                    BorderThickness="2"
                    CornerRadius="8"
                    Padding="15"
                    Margin="0,0,10,0">
                <StackPanel>
                    <TextBlock Text="User Stories Created"
                               FontSize="13"
                               Foreground="#8C8575"
                               Margin="0,0,0,8"/>
                    <TextBlock x:Name="UserStoriesCountText"
                               Text="0"
                               FontSize="28"
                               FontWeight="Bold"
                               Foreground="#D4AF37"/>
                </StackPanel>
            </Border>

            <!-- Software Flows Count -->
            <Border Grid.Column="1"
                    Background="White"
                    BorderBrush="#D4AF37"
                    BorderThickness="2"
                    CornerRadius="8"
                    Padding="15"
                    Margin="5,0">
                <StackPanel>
                    <TextBlock Text="Software Flows Created"
                               FontSize="13"
                               Foreground="#8C8575"
                               Margin="0,0,0,8"/>
                    <TextBlock x:Name="SoftwareFlowsCountText"
                               Text="0"
                               FontSize="28"
                               FontWeight="Bold"
                               Foreground="#D4AF37"/>
                </StackPanel>
            </Border>

            <!-- Test Cases Count -->
            <Border Grid.Column="2"
                    Background="White"
                    BorderBrush="#D4AF37"
                    BorderThickness="2"
                    CornerRadius="8"
                    Padding="15"
                    Margin="10,0,0,0">
                <StackPanel>
                    <TextBlock Text="Test Cases Created"
                               FontSize="13"
                               Foreground="#8C8575"
                               Margin="0,0,0,8"/>
                    <TextBlock x:Name="TestCasesCountText"
                               Text="0"
                               FontSize="28"
                               FontWeight="Bold"
                               Foreground="#D4AF37"/>
                </StackPanel>
            </Border>
        </Grid>

        <!-- Tabs -->
        <TabControl Grid.Row="2"
                    Background="White"
                    BorderBrush="#E2E1DC"
                    BorderThickness="1">
            
            <TabItem Header="User Stories">
                <Grid>
                    <DataGrid x:Name="UserStoriesGrid"
                              AutoGenerateColumns="False"
                              IsReadOnly="True"
                              GridLinesVisibility="Horizontal"
                              HeadersVisibility="Column"
                              RowBackground="White"
                              AlternatingRowBackground="#F9F9F9"
                              CanUserResizeRows="False"
                              SelectionMode="Single">
                        <DataGrid.Columns>
                            <DataGridTextColumn Header="ID" 
                                                Binding="{Binding id}" 
                                                Width="60"/>
                            <DataGridTextColumn Header="Story" 
                                                Binding="{Binding story}" 
                                                Width="*">
                                <DataGridTextColumn.ElementStyle>
                                    <Style TargetType="TextBlock">
                                        <Setter Property="TextWrapping" Value="Wrap"/>
                                        <Setter Property="Padding" Value="5"/>
                                    </Style>
                                </DataGridTextColumn.ElementStyle>
                            </DataGridTextColumn>
                        </DataGrid.Columns>
                    </DataGrid>
                </Grid>
            </TabItem>

            <TabItem Header="Software Flows">
                <Grid>
                    <DataGrid x:Name="SoftwareFlowsGrid"
                              AutoGenerateColumns="False"
                              IsReadOnly="True"
                              GridLinesVisibility="Horizontal"
                              HeadersVisibility="Column"
                              RowBackground="White"
                              AlternatingRowBackground="#F9F9F9"
                              CanUserResizeRows="False"
                              SelectionMode="Single">
                        <DataGrid.Columns>
                            <DataGridTextColumn Header="ID" 
                                                Binding="{Binding id}" 
                                                Width="60"/>
                            <DataGridTextColumn Header="Step" 
                                                Binding="{Binding step}" 
                                                Width="*">
                                <DataGridTextColumn.ElementStyle>
                                    <Style TargetType="TextBlock">
                                        <Setter Property="TextWrapping" Value="Wrap"/>
                                        <Setter Property="Padding" Value="5"/>
                                    </Style>
                                </DataGridTextColumn.ElementStyle>
                            </DataGridTextColumn>
                        </DataGrid.Columns>
                    </DataGrid>
                </Grid>
            </TabItem>

            <TabItem Header="Test Cases">
                <Grid>
                    <ScrollViewer VerticalScrollBarVisibility="Auto">
                        <ItemsControl x:Name="TestCasesList">
                            <ItemsControl.ItemTemplate>
                                <DataTemplate>
                                    <Border Background="White"
                                            BorderBrush="#E2E1DC"
                                            BorderThickness="1"
                                            CornerRadius="6"
                                            Margin="10"
                                            Padding="15">
                                        <StackPanel>
                                            <Grid Margin="0,0,0,10">
                                                <Grid.ColumnDefinitions>
                                                    <ColumnDefinition Width="Auto"/>
                                                    <ColumnDefinition Width="*"/>
                                                </Grid.ColumnDefinitions>
                                                
                                                <TextBlock Grid.Column="0"
                                                           Text="{Binding test_case_id}"
                                                           FontSize="16"
                                                           FontWeight="Bold"
                                                           Foreground="#D4AF37"/>
                                                
                                                <Border Grid.Column="1"
                                                        Background="#F0F0F0"
                                                        CornerRadius="4"
                                                        Padding="6,2"
                                                        HorizontalAlignment="Right">
                                                    <TextBlock Text="{Binding tags}"
                                                               FontSize="11"
                                                               Foreground="#666"/>
                                                </Border>
                                            </Grid>

                                            <TextBlock Text="{Binding description}"
                                                       TextWrapping="Wrap"
                                                       FontSize="14"
                                                       Foreground="#333"
                                                       Margin="0,0,0,10"/>

                                            <Separator Margin="0,5"/>

                                            <TextBlock Text="Prerequisites:"
                                                       FontWeight="SemiBold"
                                                       FontSize="13"
                                                       Margin="0,10,0,5"/>
                                            <TextBlock Text="{Binding pre_req_desc}"
                                                       TextWrapping="Wrap"
                                                       Foreground="#666"
                                                       Margin="0,0,0,10"/>

                                            <TextBlock Text="Steps:"
                                                       FontWeight="SemiBold"
                                                       FontSize="13"
                                                       Margin="0,5,0,5"/>
                                            <TextBlock Text="{Binding steps}"
                                                       TextWrapping="Wrap"
                                                       Foreground="#666"
                                                       Margin="0,0,0,10"/>

                                            <TextBlock Text="Arguments:"
                                                       FontWeight="SemiBold"
                                                       FontSize="13"
                                                       Margin="0,5,0,5"/>
                                            <TextBlock Text="{Binding arguments}"
                                                       TextWrapping="Wrap"
                                                       Foreground="#666"/>
                                        </StackPanel>
                                    </Border>
                                </DataTemplate>
                            </ItemsControl.ItemTemplate>
                        </ItemsControl>
                    </ScrollViewer>
                </Grid>
            </TabItem>
        </TabControl>

        <!-- Bottom Buttons -->
        <StackPanel Grid.Row="3"
                    Orientation="Horizontal"
                    HorizontalAlignment="Right"
                    Margin="0,20,0,0">
            <Button Content="Save to Knowledge Base"
                    Width="180"
                    Height="36"
                    Background="#D4AF37"
                    Foreground="White"
                    FontWeight="SemiBold"
                    Margin="0,0,10,0"
                    Click="SaveToKnowledgeBase_Click"/>
            
            <Button Content="Close"
                    Width="100"
                    Height="36"
                    Click="Close_Click"/>
        </StackPanel>
    </Grid>
</Window>
