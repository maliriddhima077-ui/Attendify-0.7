/**
 * ATTENDIFY — Main Global JavaScript Handler
 * Handles Sidebar toggle, Theme switcher (Dark/Light mode), Tooltips,
 * Auto-dismiss alerts, and Live Table Filtering.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Dark Mode Management
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeIcon = document.getElementById('themeIcon');
    const htmlElement = document.documentElement;

    // Load stored theme or system preference
    const storedTheme = localStorage.getItem('attendify_theme') || 'light';
    applyTheme(storedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = htmlElement.getAttribute('data-bs-theme') || 'light';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(newTheme);
            localStorage.setItem('attendify_theme', newTheme);
            
            // Dispatch event for charts to reload colors
            window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
        });
    }

    function applyTheme(theme) {
        htmlElement.setAttribute('data-bs-theme', theme);
        if (themeIcon) {
            if (theme === 'dark') {
                themeIcon.className = 'bi bi-sun-fill text-warning';
            } else {
                themeIcon.className = 'bi bi-moon-stars-fill';
            }
        }
    }

    // 2. Mobile Sidebar Toggle (+ backdrop + Esc to close)
    const sidebarToggle = document.getElementById('sidebarToggle');
    const appSidebar = document.getElementById('appSidebar');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    function setSidebar(open) {
        appSidebar.classList.toggle('show-sidebar', open);
        if (sidebarBackdrop) sidebarBackdrop.classList.toggle('show', open);
    }

    if (sidebarToggle && appSidebar) {
        sidebarToggle.addEventListener('click', () => {
            setSidebar(!appSidebar.classList.contains('show-sidebar'));
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth < 992) {
                if (!appSidebar.contains(e.target) && !sidebarToggle.contains(e.target) && appSidebar.classList.contains('show-sidebar')) {
                    setSidebar(false);
                }
            }
        });

        // Backdrop click closes
        if (sidebarBackdrop) {
            sidebarBackdrop.addEventListener('click', () => setSidebar(false));
        }

        // Escape key closes
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') setSidebar(false);
        });

        // Close after choosing a nav item on mobile
        appSidebar.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth < 992) setSidebar(false);
            });
        });
    }

    // 2b. "/" keyboard shortcut focuses global search
    const globalSearch = document.getElementById('globalSearchInput');
    document.addEventListener('keydown', (e) => {
        const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);
        if (e.key === '/' && !typing && globalSearch) {
            e.preventDefault();
            globalSearch.focus();
            globalSearch.select();
        }
    });

    // 3. Auto-dismiss Flash Alerts
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // 4. Client-side Live Table Filter (Instant Search)
    const liveFilterInput = document.getElementById('liveTableSearch');
    if (liveFilterInput) {
        liveFilterInput.addEventListener('keyup', function() {
            const filterValue = this.value.toLowerCase().trim();
            const targetTable = document.querySelector('.table-filterable tbody');
            if (!targetTable) return;

            const rows = targetTable.querySelectorAll('tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(filterValue)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    // 5. Global Search in Topbar
    const globalSearchInput = document.getElementById('globalSearchInput');
    if (globalSearchInput) {
        globalSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const q = encodeURIComponent(this.value.trim());
                if (q) {
                    window.location.href = `/students?search=${q}`;
                }
            }
        });
    }
});
