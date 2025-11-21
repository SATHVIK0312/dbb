<Page x:Class="JPMCGenAI_v1._0.RegisterPage"
      xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
      xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
      xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" 
      xmlns:d="http://schemas.microsoft.com/expression/blend/2008" 
      xmlns:local="clr-namespace:jpmc_genai"
      mc:Ignorable="d" 
      d:DesignHeight="600" d:DesignWidth="1000"
      Background="#FAF9F6"
      Title="RegisterPage">

    <Page.Resources>
        <ResourceDictionary>
            <ResourceDictionary.MergedDictionaries>
                <ResourceDictionary Source="Resources/Styles.xaml" />
            </ResourceDictionary.MergedDictionaries>
            <local:InvertedBooleanToVisibilityConverter x:Key="InvertedBooleanToVisibilityConverter" />

            <!-- Rounded TextBox Style -->
            <Style TargetType="TextBox">
                <Setter Property="Background" Value="White"/>
                <Setter Property="Foreground" Value="#333"/>
                <Setter Property="BorderBrush" Value="#D4AF37"/>
                <Setter Property="BorderThickness" Value="1"/>
                <Setter Property="Padding" Value="12,8"/>
                <Setter Property="Height" Value="40"/>
                <Setter Property="FontSize" Value="13"/>
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="TextBox">
                            <Border Background="{TemplateBinding Background}"
                                    CornerRadius="20"
                                    BorderBrush="{TemplateBinding BorderBrush}"
                                    BorderThickness="{TemplateBinding BorderThickness}">
                                <ScrollViewer x:Name="PART_ContentHost"/>
                            </Border>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>

            <!-- Rounded PasswordBox Style -->
            <Style TargetType="PasswordBox">
                <Setter Property="Background" Value="White"/>
                <Setter Property="Foreground" Value="#333"/>
                <Setter Property="BorderBrush" Value="#D4AF37"/>
                <Setter Property="BorderThickness" Value="1"/>
                <Setter Property="Padding" Value="12,8"/>
                <Setter Property="Height" Value="40"/>
                <Setter Property="FontSize" Value="13"/>
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="PasswordBox">
                            <Border Background="{TemplateBinding Background}"
                                    CornerRadius="20"
                                    BorderBrush="{TemplateBinding BorderBrush}"
                                    BorderThickness="{TemplateBinding BorderThickness}">
                                <ScrollViewer x:Name="PART_ContentHost"/>
                            </Border>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>

            <!-- Rounded Button Style -->
            <Style TargetType="Button">
                <Setter Property="Height" Value="40"/>
                <Setter Property="FontSize" Value="13"/>
                <Setter Property="FontWeight" Value="SemiBold"/>
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="Button">
                            <Border Background="{TemplateBinding Background}"
                                    CornerRadius="20"
                                    BorderBrush="{TemplateBinding BorderBrush}"
                                    BorderThickness="{TemplateBinding BorderThickness}">
                                <ContentPresenter HorizontalAlignment="Center"
                                                  VerticalAlignment="Center"/>
                            </Border>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>
        </ResourceDictionary>
    </Page.Resources>

    <Grid>
        <!-- Left Panel -->
        <StackPanel Background="#F5F3EF" VerticalAlignment="Stretch" HorizontalAlignment="Left" Width="300">
            <StackPanel VerticalAlignment="Center" HorizontalAlignment="Center" Margin="0,80,0,0">
                <TextBlock Text="jpmcAI" Foreground="#D4AF37" FontSize="36" FontWeight="Bold" TextAlignment="Center" Margin="0,0,0,10" />
                <TextBlock Text="Test Automation Platform" Foreground="#8C8575" FontSize="14" TextAlignment="Center" Margin="0,0,0,40" />
                <TextBlock Text="Create your account to get started with intelligent test execution and management."
                           Foreground="#A8A190" FontSize="12" TextWrapping="Wrap" TextAlignment="Center" LineHeight="20" />
            </StackPanel>
        </StackPanel>

        <!-- Right Panel -->
        <StackPanel HorizontalAlignment="Right" VerticalAlignment="Top" Width="400" Margin="0,50,182,0">
            <TextBlock Text="Create Account" Foreground="#333" FontSize="28" FontWeight="Bold" Margin="0,0,0,10" />
            <TextBlock Text="Join jpmcAI and start automating your tests" Foreground="#A8A190" FontSize="13" Margin="0,0,0,30" />

            <!-- Name Field -->
            <TextBlock Text="Full Name" Foreground="#555" FontSize="12" FontWeight="SemiBold" Margin="0,0,0,8" />
            <Grid Margin="0,0,0,15">
                <TextBox x:Name="NameTextBox" />
                <TextBlock Text="John Doe" Style="{StaticResource PlaceholderStyle}"
                           Visibility="{Binding Text, ElementName=NameTextBox, Converter={StaticResource InvertedBooleanToVisibilityConverter}}" Margin="20,0,0,0" />
            </Grid>

            <!-- Email Field -->
            <TextBlock Text="Email Address" Foreground="#555" FontSize="12" FontWeight="SemiBold" Margin="0,0,0,8" />
            <Grid Margin="0,0,0,15">
                <TextBox x:Name="MailTextBox" />
                <TextBlock Text="john@example.com" Style="{StaticResource PlaceholderStyle}"
                           Visibility="{Binding Text, ElementName=MailTextBox, Converter={StaticResource InvertedBooleanToVisibilityConverter}}" Margin="20,0,0,0" />
            </Grid>

            <!-- Password Field -->
            <TextBlock Text="Password" Foreground="#555" FontSize="12" FontWeight="SemiBold" Margin="0,0,0,8" />
            <Grid Margin="0,0,0,15">
                <PasswordBox x:Name="PasswordBox" />
                <TextBlock x:Name="PasswordPlaceholder" Text="Enter a strong password" Style="{StaticResource PlaceholderStyle}" Margin="20,0,0,0" />
            </Grid>

            <!-- Role Field -->
            <TextBlock Text="Role" Foreground="#555" FontSize="12" FontWeight="SemiBold" Margin="0,0,0,8" />
            <Grid Margin="0,0,0,25">
                <TextBox x:Name="RoleTextBox" />
                <TextBlock Text="QA Engineer" Style="{StaticResource PlaceholderStyle}"
                           Visibility="{Binding Text, ElementName=RoleTextBox, Converter={StaticResource InvertedBooleanToVisibilityConverter}}" Margin="20,0,0,0" />
            </Grid>

            <!-- Register Button -->
            <Button Content="Create Account" Click="SaveButton_Click"
                    Background="#D4AF37" Foreground="White" Margin="0,0,0,12" />

            <!-- Back to Login -->
            <StackPanel HorizontalAlignment="Center" Orientation="Horizontal">
                <TextBlock Text="Already have an account? " Foreground="#A8A190" FontSize="12" />
                <Button Content="Sign In" Click="BackButton_Click"
                        Background="Transparent" Foreground="#D4AF37"
                        BorderThickness="0" Padding="0" FontSize="12" FontWeight="Bold" Cursor="Hand" RenderTransformOrigin="0.494,0.546" Height="17" />
            </StackPanel>
        </StackPanel>
    </Grid>
</Page>
