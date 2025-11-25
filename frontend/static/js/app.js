// Far Reach Jobs - Main JavaScript
// HTMX configuration and utilities

document.addEventListener('DOMContentLoaded', function() {
    // HTMX configuration
    document.body.addEventListener('htmx:configRequest', function(event) {
        // Add CSRF token if needed
        // event.detail.headers['X-CSRF-Token'] = getCsrfToken();
    });

    // Handle 401 responses (redirect to login)
    document.body.addEventListener('htmx:responseError', function(event) {
        if (event.detail.xhr.status === 401) {
            window.location.href = '/login';
        }
    });

    // Debounce helper for search input
    window.debounce = function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    };
});

// Flash message helper
function showFlash(message, type = 'info') {
    const flash = document.createElement('div');
    flash.className = `flash flash-${type}`;
    flash.textContent = message;
    document.body.prepend(flash);
    setTimeout(() => flash.remove(), 5000);
}

// Logout function - sends POST request to logout endpoint
async function logout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });
        if (response.ok) {
            window.location.href = '/login';
        } else {
            showFlash('Logout failed', 'error');
        }
    } catch (error) {
        showFlash('Logout failed', 'error');
    }
}
