/**
 * Download Handler with Loading Overlay
 * Provides enhanced download functionality with loading overlays and better completion detection
 */

class DownloadHandler {
    constructor() {
        this.activeDownloads = new Set();
        this.downloadTimeouts = new Map();
    }

    /**
     * Show loading overlay with custom message
     */
    showLoadingOverlay(message = 'Processing Your Request', subtext = 'Please wait while your reports are being generated...') {
        const overlay = document.getElementById('loadingOverlay');
        if (!overlay) return;

        const textElement = overlay.querySelector('.loading-text');
        const subtextElement = overlay.querySelector('.loading-subtext');

        if (textElement) textElement.textContent = message;
        if (subtextElement) subtextElement.textContent = subtext;

        overlay.style.display = 'flex';
        overlay.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    /**
     * Hide loading overlay
     */
    hideLoadingOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        if (!overlay) return;

        overlay.classList.remove('show');
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 300); // Wait for fade out animation
        document.body.style.overflow = '';

        // Re-enable any disabled buttons
        document.querySelectorAll('.downloading').forEach(btn => {
            btn.classList.remove('downloading');
        });
    }

    /**
     * Enhanced download handler with better completion detection
     */
    handleDownload(url, options = {}) {
        const {
            message = 'Generating Report',
            subtext = 'Please wait while your report is being processed...',
            timeout = 30000, // 30 seconds default timeout
            isBulk = false,
            buttonElement = null
        } = options;

        // Prevent multiple simultaneous downloads of the same URL
        if (this.activeDownloads.has(url)) {
            return false;
        }

        // Disable the button to prevent double-clicks
        if (buttonElement) {
            buttonElement.classList.add('downloading');
        }

        this.activeDownloads.add(url);
        this.showLoadingOverlay(message, subtext);

        // Create a unique download ID for tracking
        const downloadId = Date.now() + '_' + Math.random().toString(36).substr(2, 9);

        // Method 1: Use a hidden form to trigger download
        const form = document.createElement('form');
        form.method = 'GET';
        form.action = url;
        form.style.display = 'none';
        
        // Add a hidden input with download ID for potential server-side tracking
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = 'download_id';
        hiddenInput.value = downloadId;
        form.appendChild(hiddenInput);
        
        document.body.appendChild(form);

        // Set up completion detection
        this.setupDownloadCompletion(url, downloadId, form, timeout, isBulk);

        // Submit the form to trigger download
        form.submit();

        return false; // Prevent default link behavior
    }

    /**
     * Set up download completion detection using multiple methods
     */
    setupDownloadCompletion(url, downloadId, form, timeout, isBulk) {
        let completed = false;
        
        const cleanup = () => {
            if (completed) return;
            completed = true;
            
            this.activeDownloads.delete(url);
            this.hideLoadingOverlay();
            
            if (form && form.parentNode) {
                document.body.removeChild(form);
            }
            
            if (this.downloadTimeouts.has(downloadId)) {
                clearTimeout(this.downloadTimeouts.get(downloadId));
                this.downloadTimeouts.delete(downloadId);
            }
        };

        // Method 1: Timeout-based completion (fallback)
        const timeoutId = setTimeout(() => {
            cleanup();
        }, timeout);
        
        this.downloadTimeouts.set(downloadId, timeoutId);

        // Method 2: Focus-based detection (works for some browsers)
        let focusCheckCount = 0;
        const maxFocusChecks = isBulk ? 60 : 20; // More checks for bulk downloads
        
        const checkFocus = () => {
            focusCheckCount++;
            
            if (document.hasFocus() && focusCheckCount > 3) {
                // User likely returned to the page after download dialog
                setTimeout(cleanup, 1000);
                return;
            }
            
            if (focusCheckCount < maxFocusChecks) {
                setTimeout(checkFocus, 500);
            }
        };
        
        setTimeout(checkFocus, 1000);

        // Method 3: Visibility change detection
        const handleVisibilityChange = () => {
            if (!document.hidden && focusCheckCount > 2) {
                setTimeout(() => {
                    cleanup();
                    document.removeEventListener('visibilitychange', handleVisibilityChange);
                }, 1000);
            }
        };
        
        document.addEventListener('visibilitychange', handleVisibilityChange);

        // Method 4: Mouse movement detection (user is active again)
        let mouseMovements = 0;
        const handleMouseMove = () => {
            mouseMovements++;
            if (mouseMovements > 5 && focusCheckCount > 3) {
                setTimeout(() => {
                    cleanup();
                    document.removeEventListener('mousemove', handleMouseMove);
                }, 1500);
            }
        };
        
        setTimeout(() => {
            document.addEventListener('mousemove', handleMouseMove);
        }, 2000);
    }

    /**
     * Handle single report download
     */
    handleSingleDownload(url) {
        return this.handleDownload(url, {
            message: 'Generating Report',
            subtext: 'Please wait while your report is being processed...',
            timeout: 15000, // 15 seconds for single reports
            isBulk: false
        });
    }

    /**
     * Handle bulk report download
     */
    handleBulkDownload(url) {
        return this.handleDownload(url, {
            message: 'Generating Reports',
            subtext: 'Please wait while all reports are being processed. This may take several minutes...',
            timeout: 120000, // 2 minutes for bulk downloads
            isBulk: true
        });
    }
}

// Create global instance
window.downloadHandler = new DownloadHandler();

// Global convenience functions for backward compatibility
window.handleDownloadWithLoading = function(url, message, subtext) {
    return window.downloadHandler.handleSingleDownload(url);
};

window.handleBulkDownloadWithLoading = function(url) {
    return window.downloadHandler.handleBulkDownload(url);
};

window.showLoadingOverlay = function(message, subtext) {
    window.downloadHandler.showLoadingOverlay(message, subtext);
};

window.hideLoadingOverlay = function() {
    window.downloadHandler.hideLoadingOverlay();
};
