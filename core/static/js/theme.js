// Theme handling functionality
document.addEventListener('DOMContentLoaded', () => {
    console.log('Theme script loaded');
    
    // Get the theme toggle button
    const themeToggle = document.getElementById('theme-toggle');
    console.log('Theme toggle button:', themeToggle);
    
    if (!themeToggle) {
        console.error('Theme toggle button not found!');
        return;
    }
    
    const themeIcon = themeToggle.querySelector('i');
    const themeText = themeToggle.querySelector('.theme-text');
    console.log('Theme icon:', themeIcon);
    console.log('Theme text:', themeText);
    
    // Get the current theme from localStorage or default to 'light'
    const currentTheme = localStorage.getItem('theme') || 'light';
    console.log('Current theme:', currentTheme);
    
    // Set initial theme
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeUI(currentTheme);
    
    // Theme toggle click handler
    themeToggle.addEventListener('click', () => {
        console.log('Theme toggle clicked');
        
        // Get current theme
        const currentTheme = document.documentElement.getAttribute('data-theme');
        console.log('Current theme before toggle:', currentTheme);
        
        // Toggle theme
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        console.log('New theme:', newTheme);
        
        // Update theme
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Update UI
        updateThemeUI(newTheme);
    });
    
    // Function to update theme UI
    function updateThemeUI(theme) {
        console.log('Updating theme UI for theme:', theme);
        if (theme === 'dark') {
            themeIcon.classList.remove('bi-sun-fill');
            themeIcon.classList.add('bi-moon-fill');
            if (themeText) {
                themeText.textContent = 'Dark Mode';
            }
        } else {
            themeIcon.classList.remove('bi-moon-fill');
            themeIcon.classList.add('bi-sun-fill');
            if (themeText) {
                themeText.textContent = 'Light Mode';
            }
        }
    }
}); 