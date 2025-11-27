<Window x:Class="jpmc_genai.NormalizePreviewWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Normalized Steps Review & Edit"
        Height="700" Width="1200"
        WindowStartupLocation="CenterOwner"
        ResizeMode="CanResizeWithGrip"
        Background="#F5F5F5"
        FontFamily="Segoe UI">
    
    <Grid Margin="15">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>

        <!-- Test Case Selector -->
        <StackPanel Orientation="Horizontal" Grid.Row="0" Margin="0,0,0,15">
            <TextBlock Text="Select Test Case:" 
                       VerticalAlignment="Center" 
                       FontWeight="SemiBold" 
                       Margin="0,0,10,0"/>
            <ComboBox x:Name="TestCaseSelector"
                      Width="350"
                      Height="32"
                      FontSize="14"
                      Padding="8,5"
                      SelectedIndex="0"
                      SelectionChanged="TestCaseSelector_SelectionChanged"/>
        </StackPanel>

        <!-- Side-by-Side Comparison -->
        <Grid Grid.Row="1">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="*"/>
                <ColumnDefinition Width="8"/>
                <ColumnDefinition Width="*"/>
            </Grid.ColumnDefinitions>

            <!-- Original Steps (Read-Only) -->
            <GroupBox Header="Original Steps" Grid.Column="0" Padding="8">
                <DataGrid x:Name="OriginalGrid"
                          IsReadOnly="True"
                          AutoGenerateColumns="False"
                          CanUserAddRows="False"
                          CanUserDeleteRows="False"
                          GridLinesVisibility="All"
                          HeadersVisibility="Column"
                          Background="White"
                          RowBackground="#FAFAFA"
                          AlternatingRowBackground="#F0F0F0"
                          BorderBrush="#CCCCCC">
                    <DataGrid.Columns>
                        <DataGridTextColumn Header="#" Binding="{Binding Index}" Width="60" FontWeight="Bold"/>
                        <DataGridTextColumn Header="Step Description" Binding="{Binding Step}" Width="*" />
                        <DataGridTextColumn Header="Test Data" Binding="{Binding TestDataText}" Width="220"/>
                    </DataGrid.Columns>
                </DataGrid>
            </GroupBox>

            <!-- Separator -->
            <Border Grid.Column="1" Background="#DDDDDD" Width="1" Margin="0,10"/>

            <!-- Normalized Steps (Editable) -->
            <GroupBox Header="Normalized Steps (Editable)" Grid.Column="2" Padding="8">
                <DataGrid x:Name="NormalizedGrid"
                          AutoGenerateColumns="False"
                          CanUserAddRows="False"
                          CanUserDeleteRows="False"
                          GridLinesVisibility="All"
                          HeadersVisibility="Column"
                          Background="White"
                          RowBackground="#FFFFFF"
                          AlternatingRowBackground="#E8F5E9"
                          BorderBrush="#4CAF50">
                    <DataGrid.Columns>
                        <DataGridTextColumn Header="#" Binding="{Binding Index}" Width="60" IsReadOnly="True" FontWeight="Bold"/>
                        <DataGridTextColumn Header="Step Description" Binding="{Binding Step, UpdateSourceTrigger=PropertyChanged}" Width="*"/>
                        <DataGridTextColumn Header="Test Data (Text)" Binding="{Binding TestDataText, UpdateSourceTrigger=PropertyChanged}" Width="220"/>
                    </DataGrid.Columns>
                </DataGrid>
            </GroupBox>
        </Grid>

        <!-- Action Buttons -->
        <StackPanel Grid.Row="2" Orientation="Horizontal" HorizontalAlignment="Right" Margin="0,20,0,0">
            <Button Content="Cancel" 
                    Width="130" Height="40" 
                    Margin="0,0,15,0" 
                    Click="Cancel_Click"
                    Background="#B0BEC5" 
                    Foreground="White" 
                    FontSize="14"
                    Padding="10,0"/>
            <Button Content="Save Changes" 
                    Width="160" Height="40" 
                    Click="Save_Click"
                    Background="#4CAF50" 
                    Foreground="White" 
                    FontSize="14"
                    FontWeight="SemiBold"
                    Padding="10,0"/>
        </StackPanel>
    </Grid>
</Window>
