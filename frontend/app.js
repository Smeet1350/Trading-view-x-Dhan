/**
 * TradingView x Dhan Trading System - Frontend Application
 * Phase 1: Enhanced endpoint testing and comprehensive health monitoring
 */

class TradingSystemDashboard {
    constructor() {
        this.baseUrl = 'http://localhost:8000';
        this.init();
    }
    
    init() {
        this.checkSystemStatus();
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Auto-refresh system status every 5 seconds
        setInterval(() => {
            this.checkSystemStatus();
        }, 5000);
    }
    
    async checkSystemStatus() {
        try {
            // Use enhanced health endpoint for better status monitoring
            const response = await fetch(`${this.baseUrl}/health/simple`);
            const data = await response.json();
            
            const statusElement = document.getElementById('system-status');
            const statusDot = statusElement.querySelector('.status-dot');
            const statusText = statusElement.querySelector('.status-text');
            
            if (response.ok && data.status === 'ok') {
                statusDot.className = 'status-dot online';
                statusText.textContent = 'System Online';
                statusElement.className = 'status-indicator online';
            } else {
                statusDot.className = 'status-dot offline';
                statusText.textContent = 'System Offline';
                statusElement.className = 'status-indicator offline';
            }
        } catch (error) {
            const statusElement = document.getElementById('system-status');
            const statusDot = statusElement.querySelector('.status-dot');
            const statusText = statusElement.querySelector('.status-text');
            
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'Connection Error';
            statusElement.className = 'status-indicator offline';
            
            console.error('System status check failed:', error);
        }
    }
    
    async testEndpoint(endpoint) {
        const resultElement = document.getElementById(`${endpoint.replace('/', '')}-result`);
        resultElement.innerHTML = '<div class="loading">Testing...</div>';
        
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`);
            const data = await response.json();
            
            if (response.ok) {
                resultElement.innerHTML = `
                    <div class="success">
                        <strong>✅ Success (${response.status})</strong>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    </div>
                `;
            } else {
                resultElement.innerHTML = `
                    <div class="error">
                        <strong>❌ Error (${response.status})</strong>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    </div>
                `;
            }
        } catch (error) {
            resultElement.innerHTML = `
                <div class="error">
                    <strong>❌ Connection Error</strong>
                    <pre>${error.message}</pre>
                </div>
            `;
            console.error(`Endpoint test failed for ${endpoint}:`, error);
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new TradingSystemDashboard();
});

// Global function for endpoint testing (called from HTML buttons)
function testEndpoint(endpoint) {
    if (window.dashboard) {
        window.dashboard.testEndpoint(endpoint);
    }
}
