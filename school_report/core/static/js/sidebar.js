/**
 * Sidebar toggle functionality for School Report System
 */
document.addEventListener('DOMContentLoaded', function() {
    // Toggle sidebar
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    
    if (sidebarCollapse && sidebar && content) {
        // Check if sidebar should be collapsed on mobile by default
        if (window.innerWidth < 768) {
            sidebar.classList.add('active');
            content.classList.add('active');
        }
        
        // Add click event listener
        sidebarCollapse.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            content.classList.toggle('active');
        });
        
        // Add resize event listener to handle window resizing
        window.addEventListener('resize', function() {
            if (window.innerWidth < 768) {
                sidebar.classList.add('active');
                content.classList.add('active');
            } else {
                sidebar.classList.remove('active');
                content.classList.remove('active');
            }
        });
    } else {
        console.warn('Sidebar toggle elements not found');
    }
});
