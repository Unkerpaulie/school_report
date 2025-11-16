/**
 * Idle Timeout Manager for School Report System
 * 
 * This script provides client-side idle timeout functionality that works
 * in conjunction with server-side middleware to handle session timeouts.
 * 
 * Features:
 * - Tracks user activity (mouse, keyboard, touch)
 * - Shows warning before timeout
 * - Automatically logs out idle users
 * - Works even when tabs are closed (server-side backup)
 */

class IdleTimeoutManager {
    constructor(options = {}) {
        // Configuration (times in milliseconds)
        this.idleTimeout = options.idleTimeout || (30 * 60 * 1000); // 30 minutes default
        this.warningTime = options.warningTime || (5 * 60 * 1000);  // 5 minutes warning
        this.checkInterval = options.checkInterval || 1000;         // Check every second
        
        // State tracking
        this.lastActivity = Date.now();
        this.warningShown = false;
        this.isActive = true;
        
        // Timer references
        this.checkTimer = null;
        this.warningTimer = null;
        
        // Activity events to monitor
        this.activityEvents = [
            'mousedown', 'mousemove', 'keypress', 'scroll', 
            'touchstart', 'click', 'focus'
        ];
        
        this.init();
    }
    
    init() {
        // Only initialize for authenticated users
        if (!document.body.dataset.userAuthenticated) {
            return;
        }
        
        // Bind activity listeners
        this.bindActivityListeners();
        
        // Start monitoring
        this.startMonitoring();
        
        console.log('Idle timeout manager initialized');
    }
    
    bindActivityListeners() {
        // Add event listeners for user activity
        this.activityEvents.forEach(event => {
            document.addEventListener(event, () => this.recordActivity(), true);
        });
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.recordActivity();
            }
        });
    }
    
    recordActivity() {
        this.lastActivity = Date.now();
        
        // Hide warning if it's showing
        if (this.warningShown) {
            this.hideWarning();
        }
    }
    
    startMonitoring() {
        this.checkTimer = setInterval(() => {
            this.checkIdleStatus();
        }, this.checkInterval);
    }
    
    checkIdleStatus() {
        const now = Date.now();
        const idleTime = now - this.lastActivity;
        const timeUntilTimeout = this.idleTimeout - idleTime;
        
        // Show warning if approaching timeout
        if (timeUntilTimeout <= this.warningTime && !this.warningShown) {
            this.showWarning(Math.ceil(timeUntilTimeout / 1000));
        }
        
        // Logout if timeout exceeded
        if (idleTime >= this.idleTimeout) {
            this.performLogout();
        }
    }
    
    showWarning(secondsLeft) {
        this.warningShown = true;
        
        // Create warning modal
        const modal = this.createWarningModal(secondsLeft);
        document.body.appendChild(modal);
        
        // Show the modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Update countdown
        this.warningTimer = setInterval(() => {
            secondsLeft--;
            const countdownElement = modal.querySelector('#timeout-countdown');
            if (countdownElement) {
                countdownElement.textContent = secondsLeft;
            }
            
            if (secondsLeft <= 0) {
                clearInterval(this.warningTimer);
                bootstrapModal.hide();
                this.performLogout();
            }
        }, 1000);
    }
    
    createWarningModal(secondsLeft) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'idle-timeout-warning';
        modal.setAttribute('data-bs-backdrop', 'static');
        modal.setAttribute('data-bs-keyboard', 'false');
        
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title">
                            <i class="bi bi-exclamation-triangle"></i> Session Timeout Warning
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <p class="mb-3">Your session will expire in:</p>
                        <h2 class="text-danger mb-3">
                            <span id="timeout-countdown">${secondsLeft}</span> seconds
                        </h2>
                        <p class="text-muted">Click "Stay Logged In" to continue your session.</p>
                    </div>
                    <div class="modal-footer justify-content-center">
                        <button type="button" class="btn btn-primary" onclick="idleManager.extendSession()">
                            <i class="bi bi-clock-history"></i> Stay Logged In
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="idleManager.performLogout()">
                            <i class="bi bi-box-arrow-right"></i> Logout Now
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return modal;
    }
    
    hideWarning() {
        this.warningShown = false;
        
        // Clear warning timer
        if (this.warningTimer) {
            clearInterval(this.warningTimer);
            this.warningTimer = null;
        }
        
        // Hide and remove modal
        const modal = document.getElementById('idle-timeout-warning');
        if (modal) {
            const bootstrapModal = bootstrap.Modal.getInstance(modal);
            if (bootstrapModal) {
                bootstrapModal.hide();
            }
            modal.remove();
        }
    }
    
    extendSession() {
        // Record activity to reset timer
        this.recordActivity();
        
        // Make a request to server to update session activity
        fetch('/debug/session/', {
            method: 'GET',
            credentials: 'same-origin'
        }).catch(error => {
            console.log('Session refresh request failed:', error);
        });
        
        console.log('Session extended');
    }
    
    performLogout() {
        // Clear all timers
        if (this.checkTimer) {
            clearInterval(this.checkTimer);
        }
        if (this.warningTimer) {
            clearInterval(this.warningTimer);
        }
        
        // Redirect to custom logout
        window.location.href = '/logout/';
    }
    
    destroy() {
        // Clean up timers and event listeners
        if (this.checkTimer) {
            clearInterval(this.checkTimer);
        }
        if (this.warningTimer) {
            clearInterval(this.warningTimer);
        }
        
        this.activityEvents.forEach(event => {
            document.removeEventListener(event, this.recordActivity, true);
        });
    }
}

// Initialize idle timeout manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Get timeout settings from Django (passed via template)
    const timeoutMinutes = parseInt(document.body.dataset.idleTimeoutMinutes) || 30;
    const timeoutMs = timeoutMinutes * 60 * 1000;
    
    // Initialize the idle manager
    window.idleManager = new IdleTimeoutManager({
        idleTimeout: timeoutMs,
        warningTime: 5 * 60 * 1000  // 5 minutes warning
    });
});
