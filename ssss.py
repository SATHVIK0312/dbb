<Window x:Class="jpmc_genai.TestPlanViewWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Test Plan Viewer"
        Height="680" Width="1200"
        WindowStartupLocation="CenterOwner"
        Background="#FAF9F6"
        ResizeMode="CanResize"
        FontFamily="Segoe UI">

    <Window.Resources>
        <!-- JPMC Flux Gold & Style -->
        <SolidColorBrush x:Key="Gold" Color="#D4AF37"/>
        <SolidColorBrush x:Key="LightGold" Color="#FFF8F0"/>
        <SolidColorBrush x:Key="DarkText" Color="#333333"/>
        <SolidColorBrush x:Key="BorderBrush" Color="#E2E1DC"/>

        <!-- Clean Modern DataGrid -->
        <Style TargetType="DataGrid">
            <Setter Property="Background" Value="White"/>
            <Setter Property="BorderBrush" Value="{StaticResource BorderBrush}"/>
            <Setter Property="BorderThickness" Value="1"/>
            <Setter Property="RowBackground" Value="White"/>
            <Setter Property="AlternatingRowBackground" Value="#FFFBF5"/>
            <Setter Property="GridLinesVisibility" Value="Horizontal"/>
            <Setter Property="HorizontalGridLinesBrush" Value="#EEEEEE"/>
            <Setter Property="HeadersVisibility" Value="Column"/>
            <Setter Property="ColumnHeaderHeight" Value="44"/>
            <Setter Property="RowHeight" Value="48"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="IsReadOnly" Value="True"/>
            <Setter Property="AutoGenerateColumns" Value="False"/>
            <Setter Property="CanUserAddRows" Value="False"/>
            <Setter Property="SelectionMode" Value="Single"/>
            <!-- This ensures scrollbars appear when needed -->
            <Setter Property="VerticalScrollBarVisibility" Value="Auto"/>
            <Setter Property="HorizontalScrollBarVisibility" Value="Auto"/>
        </Style>

        <Style TargetType="DataGridColumnHeader">
            <Setter Property="Background" Value="{StaticResource LightGold}"/>
            <Setter Property="Foreground" Value="#D4AF37"/>
            <Setter Property="FontWeight" Value="SemiBold"/>
            <Setter Property="FontSize" Value="14"/>
            <Setter Property="Padding" Value="16,0"/>
            <Setter Property="HorizontalContentAlignment" Value="Left"/>
            <Setter Property="BorderBrush" Value="{StaticResource BorderBrush}"/>
            <Setter Property="BorderThickness" Value="0,0,0,1"/>
        </Style>

        <Style TargetType="DataGridCell">
            <Setter Property="Padding" Value="16,0"/>
            <Style.Triggers>
                <Trigger Property="IsSelected" Value="True">
                    <Setter Property="Background" Value="#FFF0E0"/>
                    <Setter Property="BorderBrush" Value="#D4AF37"/>
                </Trigger>
            </Style.Triggers>
        </Style>

        <!-- Gold Close Button -->
        <Style TargetType="Button">
            <Setter Property="Background" Value="#D4AF37"/>
            <Setter Property="Foreground" Value="White"/>
            <Setter Property="FontWeight" Value="SemiBold"/>
            <Setter Property="Padding" Value="24,12"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Cursor" Value="Hand"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border Background="{TemplateBinding Background}" 
                                CornerRadius="14"
                                Padding="{TemplateBinding Padding}">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter Property="Background" Value="#B8952D"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <Style x:Key="NumberColumnStyle" TargetType="DataGridCell">
            <Setter Property="Padding" Value="16,0"/>
            <Setter Property="TextBlock.TextAlignment" Value="Center"/>
            <Setter Property="TextBlock.FontWeight" Value="SemiBold"/>
            <Style.Triggers>
                <Trigger Property="IsSelected" Value="True">
                    <Setter Property="Background" Value="#FFF0E0"/>
                    <Setter Property="BorderBrush" Value="#D4AF37"/>
                </Trigger>
            </Style.Triggers>
        </Style>

        <Style x:Key="TypeColumnStyle" TargetType="DataGridCell">
            <Setter Property="Padding" Value="16,0"/>
            <Style.Triggers>
                <Trigger Property="IsSelected" Value="True">
                    <Setter Property="Background" Value="#FFF0E0"/>
                    <Setter Property="BorderBrush" Value="#D4AF37"/>
                </Trigger>
            </Style.Triggers>
        </Style>
    </Window.Resources>

    <!-- Main Card with Shadow -->
    <Border Margin="24" Background="White" CornerRadius="24" BorderBrush="#E2E1DC" BorderThickness="1">
        <Border.Effect>
            <DropShadowEffect BlurRadius="30" Opacity="0.15" ShadowDepth="10" Color="#000000"/>
        </Border.Effect>

        <!-- This ScrollViewer is the ONLY change needed for full scrolling -->
        <ScrollViewer VerticalScrollBarVisibility="Auto" 
                      HorizontalScrollBarVisibility="Disabled"
                      Padding="0,0,0,20">
            <Grid Margin="32">
                <Grid.RowDefinitions>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="*"/>
                    <RowDefinition Height="Auto"/>
                </Grid.RowDefinitions>

                <!-- Header -->
                <StackPanel Grid.Row="0" Margin="0,0,0,24">
                    <TextBlock Text="Generated Test Plan"
                               FontSize="30"
                               FontWeight="Bold"
                               Foreground="#333333"/>
                    <TextBlock Text="AI-generated execution plan with test data"
                               FontSize="15"
                               Foreground="#8C8575"
                               Margin="0,8,0,0"/>
                </StackPanel>

                <!-- Test Plan Table (now inside ScrollViewer) -->
                <Border Grid.Row="1" 
                        Background="White" 
                        CornerRadius="18" 
                        BorderBrush="#E2E1DC" 
                        BorderThickness="1"
                        Padding="0">
                    <DataGrid x:Name="TestPlanGrid">
                        <DataGrid.Columns>
                            <DataGridTextColumn Header="#" 
                                                Binding="{Binding RowNumber}" 
                                                Width="50"
                                                CellStyle="{StaticResource NumberColumnStyle}"/>

                            <DataGridTextColumn Header="Test Case ID" 
                                                Binding="{Binding TestCaseId}" 
                                                Width="140"/>

                            <DataGridTextColumn Header="Step #" 
                                                Binding="{Binding StepNumber}" 
                                                Width="60"
                                                CellStyle="{StaticResource NumberColumnStyle}"/>

                            <DataGridTextColumn Header="Step Description" 
                                                Binding="{Binding Step}" 
                                                Width="2*"/>

                            <DataGridTextColumn Header="Test Data / Parameters" 
                                                Binding="{Binding TestData}" 
                                                Width="1.5*"/>

                            <DataGridTextColumn Header="Type" 
                                                Binding="{Binding TestCaseType}" 
                                                Width="140"
                                                CellStyle="{StaticResource TypeColumnStyle}"/>
                        </DataGrid.Columns>
                    </DataGrid>
                </Border>

                <!-- Footer -->
                <StackPanel Grid.Row="2" 
                            Orientation="Horizontal" 
                            HorizontalAlignment="Right" 
                            Margin="0,32,0,8">
                    <Button Content="Close" 
                            Click="Close_Click" 
                            Width="140" 
                            Height="48"/>
                </StackPanel>
            </Grid>
        </ScrollViewer>
    </Border>
</Window>
