// TradingView x Dhan Trading System - Frontend JavaScript

class TradingSystemFrontend {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000';
        this.webhookToken = 'test_webhook_token'; // This should come from environment
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkSystemStatus();
        this.loadAlerts();
        this.setDefaultTimestamp();
    }

    setupEventListeners() {
        // Webhook form submission
        const webhookForm = document.getElementById('webhook-form');
        if (webhookForm) {
            webhookForm.addEventListener('submit', (e) => this.handleWebhookSubmit(e));
        }

        // Refresh alerts button
        const refreshBtn = document.getElementById('refresh-alerts');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadAlerts());
        }
    }

    setDefaultTimestamp() {
        const timestampInput = document.getElementById('webhook-timestamp');
        if (timestampInput) {
            const now = new Date();
            const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
                .toISOString()
                .slice(0, 16);
            timestampInput.value = localDateTime;
        }
    }

    async checkSystemStatus() {
        try {
            // Check backend API
            await this.checkBackendStatus();
            
            // Check webhook endpoint
            await this.checkWebhookStatus();
            
            // Check database status
            await this.checkDatabaseStatus();
        } catch (error) {
            console.error('Error checking system status:', error);
        }
    }

    async checkBackendStatus() {
        const statusElement = document.getElementById('backend-status');
        if (!statusElement) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/healthz`);
            if (response.ok) {
                statusElement.textContent = 'Online';
                statusElement.className = 'status-indicator online';
            } else {
                throw new Error('Backend not responding');
            }
        } catch (error) {
            statusElement.textContent = 'Offline';
            statusElement.className = 'status-indicator offline';
        }
    }

    async checkWebhookStatus() {
        const statusElement = document.getElementById('webhook-status');
        if (!statusElement) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/webhook/status`);
            if (response.ok) {
                statusElement.textContent = 'Active';
                statusElement.className = 'status-indicator online';
            } else {
                throw new Error('Webhook endpoint not responding');
            }
        } catch (error) {
            statusElement.textContent = 'Inactive';
            statusElement.className = 'status-indicator offline';
        }
    }

    async checkDatabaseStatus() {
        const statusElement = document.getElementById('database-status');
        if (!statusElement) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/webhook/status`);
            if (response.ok) {
                const data = await response.json();
                if (data.alert_count !== undefined) {
                    statusElement.textContent = 'Connected';
                    statusElement.className = 'status-indicator online';
                } else {
                    throw new Error('Database not accessible');
                }
            } else {
                throw new Error('Database status check failed');
            }
        } catch (error) {
            statusElement.textContent = 'Disconnected';
            statusElement.className = 'status-indicator offline';
        }
    }

    async handleWebhookSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const webhookData = {
            id: formData.get('id'),
            symbol: formData.get('symbol'),
            signal: formData.get('signal'),
            ts: new Date(formData.get('ts')).toISOString()
        };

        try {
            await this.sendWebhook(webhookData);
        } catch (error) {
            console.error('Error sending webhook:', error);
            this.showWebhookResult('Error sending webhook: ' + error.message, 'error');
        }
    }

    async sendWebhook(webhookData) {
        const response = await fetch(`${this.apiBaseUrl}/webhook`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-WEBHOOK-TOKEN': this.webhookToken
            },
            body: JSON.stringify(webhookData)
        });

        const result = await response.json();
        
        if (response.ok) {
            this.showWebhookResult(result, result.status === 'accepted' ? 'success' : 'info');
            // Refresh alerts after successful webhook
            if (result.status === 'accepted') {
                setTimeout(() => this.loadAlerts(), 1000);
            }
        } else {
            this.showWebhookResult('Error: ' + result.detail, 'error');
        }
    }

    showWebhookResult(message, type = 'info') {
        const resultsContainer = document.getElementById('webhook-results');
        if (!resultsContainer) return;

        const resultDiv = document.createElement('div');
        resultDiv.className = `result ${type}`;
        resultDiv.innerHTML = `
            <strong>${new Date().toLocaleTimeString()}</strong>: ${message}
        `;

        resultsContainer.appendChild(resultDiv);
        
        // Keep only last 10 results
        const results = resultsContainer.querySelectorAll('.result');
        if (results.length > 10) {
            results[0].remove();
        }
    }

    async loadAlerts() {
        const alertsList = document.getElementById('alerts-list');
        if (!alertsList) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/webhook/status`);
            if (response.ok) {
                const data = await response.json();
                this.displayAlerts(data.alert_count);
            } else {
                alertsList.innerHTML = '<p>Error loading alerts</p>';
            }
        } catch (error) {
            alertsList.innerHTML = '<p>Failed to connect to server</p>';
        }
    }

    displayAlerts(alertCount) {
        const alertsList = document.getElementById('alerts-list');
        if (!alertsList) return;

        if (alertCount === 0) {
            alertsList.innerHTML = '<p>No alerts stored yet.</p>';
            return;
        }

        alertsList.innerHTML = `
            <div class="alert-item">
                <h4>System Status</h4>
                <p><strong>Total Alerts:</strong> ${alertCount}</p>
                <p><strong>Last Updated:</strong> ${new Date().toLocaleString()}</p>
            </div>
        `;
    }

    // Utility method to format timestamps
    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }
}

// Initialize the frontend when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TradingSystemFrontend();
});

// Export for testing purposes
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TradingSystemFrontend;
}
