/**
 * Dark Mode Toggle Functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const htmlElement = document.documentElement;
    
    // Check for saved user preference
    const savedTheme = localStorage.getItem('theme');
    
    // Apply saved theme or default to light
    if (savedTheme === 'dark') {
        htmlElement.setAttribute('data-theme', 'dark');
        darkModeToggle.checked = true;
    } else {
        htmlElement.setAttribute('data-theme', 'light');
        darkModeToggle.checked = false;
    }
    
    // Listen for toggle changes
    darkModeToggle.addEventListener('change', function() {
        if (this.checked) {
            htmlElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            htmlElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    });
    
    // Check for system preference if no saved preference
    if (!savedTheme) {
        const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
        if (prefersDarkScheme.matches) {
            htmlElement.setAttribute('data-theme', 'dark');
            darkModeToggle.checked = true;
            localStorage.setItem('theme', 'dark');
        }
    }
}); 