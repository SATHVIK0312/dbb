<Page x:Class="JPMCGenAI_v1._0.KnowledgeCenterPage"
      xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
      xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
      Background="#FAF9F6"
      Loaded="Page_Loaded">

    <Page.Resources>
        <!-- === REUSED SIDEBAR STYLES === -->
        <Style TargetType="Button" x:Key="SidebarButtonTheme">
            <Setter Property="Background" Value="#FFF6EC"/>
            <Setter Property="Foreground" Value="#333"/>
            <Setter Property="FontFamily" Value="Segoe UI"/>
            <Setter Property="FontWeight" Value="SemiBold"/>
            <Setter Property="Width" Value="150"/>
            <Setter Property="Height" Value="34"/>
            <Setter Property="BorderBrush" Value="#D4AF37"/>
            <Setter Property="BorderThickness" Value="1"/>
            <Setter Property="Cursor" Value="Hand"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border x:Name="border" Background="{TemplateBinding Background}"
                                BorderBrush="{TemplateBinding BorderBrush}"
                                BorderThickness="{TemplateBinding BorderThickness}"
                                CornerRadius="10">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter TargetName="border" Property="Effect">
                                    <Setter.Value>
                                        <DropShadowEffect BlurRadius="12" ShadowDepth="0" Opacity="0.35"/>
                                    </Setter.Value>
                                </Setter>
                                <Setter TargetName="border" Property="Background" Value="#D4AF37"/>
                                <Setter Property="Foreground" Value="White"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <Style TargetType="Button" x:Key="ActiveSidebarButtonTheme" BasedOn="{StaticResource SidebarButtonTheme}">
            <Setter Property="IsEnabled" Value="False"/>
            <Setter Property="Foreground" Value="#D4AF37"/>
            <Setter Property="BorderBrush" Value="#D4AF37"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border Background="#FFF6EC" BorderBrush="#D4AF37" CornerRadius="10" BorderThickness="0,0,0,3">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                        </Border>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>
    </Page.Resources>

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
            <Border.Effect>
                <DropShadowEffect BlurRadius="18" ShadowDepth="3" Opacity="0.18"/>
            </Border.Effect>
            <Grid>
                <Grid.RowDefinitions>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="*"/>
                    <RowDefinition Height="Auto"/>
                </Grid.RowDefinitions>

                <Border Background="#D4AF37" Padding="18" CornerRadius="0,18,0,0">
                    <TextBlock Text="JPMC Flux" 
                               Foreground="White" 
                               FontSize="22" 
                               FontWeight="Bold" 
                               HorizontalAlignment="Center"/>
                </Border>

                <StackPanel Grid.Row="1" Margin="20,25,20,10">
                    <Button Content="Project Dashboard" 
                            Click="BackToDashboard_Click" 
                            Style="{StaticResource SidebarButtonTheme}" 
                            Margin="0,0,0,12"/>
                    
                    <Button Content="Manage Test Case" 
                            Click="UploadTestCase_Click" 
                            Style="{StaticResource SidebarButtonTheme}" 
                            Margin="0,0,0,12"/>
                    
                    <Button Content="Smart Executor" 
                            Click="AITestExecutor_Click" 
                            Style="{StaticResource SidebarButtonTheme}" 
                            Margin="0,0,0,12"/>
                    
                    <Button Content="Script Generator" 
                            Click="ScriptGenerator_Click" 
                            Style="{StaticResource SidebarButtonTheme}" 
                            Margin="0,0,0,12"/>
                    
                    <Button Content="Knowledge Center" 
                            Style="{StaticResource ActiveSidebarButtonTheme}" 
                            Margin="0,0,0,12"/>
                    
                    <Button Content="Execution Log" 
                            Click="ExecutionLog_Click" 
                            Style="{StaticResource SidebarButtonTheme}" 
                            Margin="0,0,0,12"/>
                </StackPanel>

                <Border Grid.Row="2" 
                        Margin="15,20" 
                        Padding="18" 
                        Background="White" 
                        CornerRadius="12" 
                        BorderBrush="#E2E1DC" 
                        BorderThickness="1">
                    <Border.Effect>
                        <DropShadowEffect BlurRadius="10" Opacity="0.15" ShadowDepth="2"/>
                    </Border.Effect>
                    <StackPanel>
                        <TextBlock x:Name="ProjectTitleTextBlock" 
                                   Foreground="#333" 
                                   FontWeight="Bold" 
                                   FontSize="20" 
                                   Margin="0,0,0,5"/>
                        <TextBlock x:Name="ProjectDetailsTextBlock" 
                                   Foreground="#8C8575" 
                                   FontSize="11"/>
                        <Button Content="Change Project" 
                                Style="{StaticResource SidebarButtonTheme}" 
                                Click="ChangeProject_Click" 
                                Margin="0,10,0,0"/>
                    </StackPanel>
                </Border>
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
