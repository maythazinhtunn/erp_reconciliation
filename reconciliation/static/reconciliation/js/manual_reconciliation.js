/**
 * Manual Reconciliation JavaScript
 * Handles all functionality for the manual reconciliation admin page
 */

class ManualReconciliation {
    constructor() {
        this.unmatchedTransactions = [];
        this.unpaidInvoices = [];
        this.recentMatches = [];
        this.selectedTransaction = null;
        this.selectedInvoice = null;
        this.stats = {};
        
        // Initialize the application
        this.init();
    }

    init() {
        console.log('Initializing Manual Reconciliation...');
        this.bindEvents();
        this.loadAllData();
        this.setupSearchFunctionality();
    }

    bindEvents() {
        // Modal events
        document.getElementById('confirmMatchBtn').addEventListener('click', () => {
            this.confirmMatch();
        });

        // Search events
        document.getElementById('transactionSearch').addEventListener('input', (e) => {
            this.filterTransactions(e.target.value);
        });

        document.getElementById('invoiceSearch').addEventListener('input', (e) => {
            this.filterInvoices(e.target.value);
        });

        // CSRF token setup for API calls
        this.setupCSRF();
    }

    setupCSRF() {
        // Get CSRF token from Django
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                         document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        if (csrfToken) {
            this.csrfToken = csrfToken;
        } else {
            // Try to get from cookie
            this.csrfToken = this.getCookie('csrftoken');
        }
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    async loadAllData() {
        this.showLoading(true);
        
        try {
            await Promise.all([
                this.loadUnmatchedTransactions(),
                this.loadUnpaidInvoices(),
                this.loadRecentMatches(),
                this.loadStats()
            ]);
            
            this.renderAll();
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Failed to load data. Please refresh the page.');
        } finally {
            this.showLoading(false);
        }
    }

    async loadUnmatchedTransactions() {
        try {
            const response = await fetch('/api/bank/unmatched/');
            if (!response.ok) throw new Error('Failed to fetch transactions');
            this.unmatchedTransactions = await response.json();
        } catch (error) {
            console.error('Error loading unmatched transactions:', error);
            throw error;
        }
    }

    async loadUnpaidInvoices() {
        try {
            const response = await fetch('/api/invoices/unpaid/');
            if (!response.ok) throw new Error('Failed to fetch invoices');
            this.unpaidInvoices = await response.json();
        } catch (error) {
            console.error('Error loading unpaid invoices:', error);
            throw error;
        }
    }

    async loadRecentMatches() {
        try {
            const response = await fetch('/api/reconciliation/logs/');
            if (!response.ok) throw new Error('Failed to fetch logs');
            const logs = await response.json();
            
            // Filter for manual matches only and recent ones
            this.recentMatches = logs
                .filter(log => log.matched_by === 'manual' && log.invoice_id)
                .slice(0, 10); // Get latest 10 matches
        } catch (error) {
            console.error('Error loading recent matches:', error);
            throw error;
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/reconciliation/stats/');
            if (!response.ok) throw new Error('Failed to fetch stats');
            this.stats = await response.json();
        } catch (error) {
            console.error('Error loading stats:', error);
            throw error;
        }
    }

    renderAll() {
        this.renderStats();
        this.renderTransactions();
        this.renderInvoices();
        this.renderRecentMatches();
    }

    renderStats() {
        document.getElementById('unmatchedCount').textContent = this.stats.transactions?.unmatched || 0;
        document.getElementById('unpaidCount').textContent = this.stats.invoices?.unpaid || 0;
        document.getElementById('matchedToday').textContent = this.stats.reconciliation?.manual_matches || 0;
        document.getElementById('matchRate').textContent = 
            (this.stats.transactions?.match_rate || 0) + '%';
    }

    renderTransactions(transactions = this.unmatchedTransactions) {
        const tbody = document.getElementById('transactionsTable');
        
        if (transactions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-4 empty-state">
                        <i class="fas fa-check-circle text-success"></i>
                        <p class="mb-0">No unmatched transactions found!</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = transactions.map(transaction => `
            <tr class="transaction-row" data-transaction-id="${transaction.id}">
                <td>${this.formatDate(transaction.date)}</td>
                <td>
                    <span class="amount ${transaction.amount >= 0 ? 'positive' : 'negative'}">
                        $${this.formatAmount(Math.abs(transaction.amount))}
                    </span>
                </td>
                <td>
                    <span class="text-truncate d-inline-block" style="max-width: 200px;" 
                          title="${transaction.description}">
                        ${transaction.description}
                    </span>
                </td>
                <td>${transaction.reference_number || '-'}</td>
                <td>
                    <button class="btn btn-select btn-sm" 
                            onclick="reconciliation.selectTransaction(${transaction.id})">
                        <i class="fas fa-hand-pointer"></i> Select
                    </button>
                </td>
            </tr>
        `).join('');
    }

    renderInvoices(invoices = this.unpaidInvoices) {
        const tbody = document.getElementById('invoicesTable');
        
        if (invoices.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-4 empty-state">
                        <i class="fas fa-check-circle text-success"></i>
                        <p class="mb-0">No unpaid invoices found!</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = invoices.map(invoice => `
            <tr class="invoice-row" data-invoice-id="${invoice.id}">
                <td>#${invoice.id}</td>
                <td>
                    <span title="${invoice.customer_email}">
                        ${invoice.customer_name}
                    </span>
                </td>
                <td>
                    <span class="amount positive">
                        $${this.formatAmount(invoice.amount_due)}
                    </span>
                </td>
                <td>${invoice.reference_number || '-'}</td>
                <td>
                    <button class="btn btn-select btn-sm" 
                            onclick="reconciliation.selectInvoice(${invoice.id})">
                        <i class="fas fa-hand-pointer"></i> Select
                    </button>
                </td>
            </tr>
        `).join('');
    }

    renderRecentMatches() {
        const tbody = document.getElementById('recentMatchesTable');
        
        if (this.recentMatches.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 empty-state">
                        <i class="fas fa-history"></i>
                        <p class="mb-0">No recent manual matches found.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.recentMatches.map(match => `
            <tr>
                <td>${this.formatDateTime(match.timestamp)}</td>
                <td>
                    <span class="badge bg-primary">#${match.transaction_id}</span>
                    <small class="d-block text-muted">
                        ${match.transaction_reference || 'No ref'}
                    </small>
                </td>
                <td>
                    <span class="badge bg-success">#${match.invoice_id}</span>
                </td>
                <td>${match.invoice_customer || 'N/A'}</td>
                <td>
                    <span class="amount positive">
                        $${this.formatAmount(match.transaction_amount)}
                    </span>
                </td>
                <td>
                    <button class="btn btn-undo btn-sm" 
                            onclick="reconciliation.undoMatch(${match.transaction_id})"
                            title="Undo this match">
                        <i class="fas fa-undo"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    selectTransaction(transactionId) {
        // Clear previous selection
        document.querySelectorAll('.transaction-row').forEach(row => {
            row.classList.remove('selected');
        });

        // Select new transaction
        const row = document.querySelector(`[data-transaction-id="${transactionId}"]`);
        if (row) {
            row.classList.add('selected');
            this.selectedTransaction = this.unmatchedTransactions.find(t => t.id === transactionId);
            
            // If both transaction and invoice are selected, enable matching
            if (this.selectedTransaction && this.selectedInvoice) {
                this.showMatchModal();
            }
        }
    }

    selectInvoice(invoiceId) {
        // Clear previous selection
        document.querySelectorAll('.invoice-row').forEach(row => {
            row.classList.remove('selected');
        });

        // Select new invoice
        const row = document.querySelector(`[data-invoice-id="${invoiceId}"]`);
        if (row) {
            row.classList.add('selected');
            this.selectedInvoice = this.unpaidInvoices.find(i => i.id === invoiceId);
            
            // If both transaction and invoice are selected, enable matching
            if (this.selectedTransaction && this.selectedInvoice) {
                this.showMatchModal();
            }
        }
    }

    showMatchModal() {
        if (!this.selectedTransaction || !this.selectedInvoice) return;

        // Populate modal with transaction and invoice details
        document.getElementById('modalTransactionAmount').textContent = 
            '$' + this.formatAmount(Math.abs(this.selectedTransaction.amount));
        document.getElementById('modalTransactionDate').textContent = 
            this.formatDate(this.selectedTransaction.date);
        document.getElementById('modalTransactionDescription').textContent = 
            this.selectedTransaction.description;
        document.getElementById('modalTransactionReference').textContent = 
            this.selectedTransaction.reference_number || 'N/A';

        document.getElementById('modalInvoiceId').textContent = '#' + this.selectedInvoice.id;
        document.getElementById('modalInvoiceCustomer').textContent = this.selectedInvoice.customer_name;
        document.getElementById('modalInvoiceAmount').textContent = 
            '$' + this.formatAmount(this.selectedInvoice.amount_due);
        document.getElementById('modalInvoiceReference').textContent = 
            this.selectedInvoice.reference_number || 'N/A';

        // Check for amount mismatch
        const transactionAmount = Math.abs(this.selectedTransaction.amount);
        const invoiceAmount = this.selectedInvoice.amount_due;
        const amountMismatch = Math.abs(transactionAmount - invoiceAmount) > 0.01;

        const warningElement = document.getElementById('amountMismatchWarning');
        if (amountMismatch) {
            warningElement.style.display = 'block';
        } else {
            warningElement.style.display = 'none';
        }

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('matchModal'));
        modal.show();
    }

    async confirmMatch() {
        if (!this.selectedTransaction || !this.selectedInvoice) return;

        this.showLoading(true);

        try {
            const response = await fetch('/api/bank/match/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    transaction_id: this.selectedTransaction.id,
                    invoice_id: this.selectedInvoice.id
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to match');
            }

            // Success - hide modal and refresh data
            const modal = bootstrap.Modal.getInstance(document.getElementById('matchModal'));
            modal.hide();

            this.showSuccess('Transaction matched successfully!');
            
            // Clear selections
            this.selectedTransaction = null;
            this.selectedInvoice = null;
            
            // Refresh data
            await this.loadAllData();

        } catch (error) {
            console.error('Error confirming match:', error);
            this.showError('Failed to match: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async undoMatch(transactionId) {
        if (!confirm('Are you sure you want to undo this match? This will mark the invoice as unpaid again.')) {
            return;
        }

        this.showLoading(true);

        try {
            const response = await fetch('/api/reconciliation/reprocess/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    transaction_id: transactionId
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to undo match');
            }

            this.showSuccess('Match undone successfully!');
            await this.loadAllData();

        } catch (error) {
            console.error('Error undoing match:', error);
            this.showError('Failed to undo match: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    setupSearchFunctionality() {
        // Transaction search
        const transactionSearch = document.getElementById('transactionSearch');
        transactionSearch.addEventListener('input', (e) => {
            this.filterTransactions(e.target.value);
        });

        // Invoice search
        const invoiceSearch = document.getElementById('invoiceSearch');
        invoiceSearch.addEventListener('input', (e) => {
            this.filterInvoices(e.target.value);
        });
    }

    filterTransactions(searchTerm) {
        const filtered = this.unmatchedTransactions.filter(transaction => {
            const term = searchTerm.toLowerCase();
            return (
                transaction.description.toLowerCase().includes(term) ||
                transaction.reference_number?.toLowerCase().includes(term) ||
                transaction.amount.toString().includes(term) ||
                transaction.date.includes(term)
            );
        });
        this.renderTransactions(filtered);
    }

    filterInvoices(searchTerm) {
        const filtered = this.unpaidInvoices.filter(invoice => {
            const term = searchTerm.toLowerCase();
            return (
                invoice.customer_name.toLowerCase().includes(term) ||
                invoice.customer_email?.toLowerCase().includes(term) ||
                invoice.reference_number?.toLowerCase().includes(term) ||
                invoice.amount_due.toString().includes(term) ||
                invoice.id.toString().includes(term)
            );
        });
        this.renderInvoices(filtered);
    }

    // Utility functions
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    formatDateTime(dateTimeString) {
        const date = new Date(dateTimeString);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatAmount(amount) {
        return parseFloat(amount).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        overlay.style.display = show ? 'flex' : 'none';
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} 
                          alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 10000; min-width: 300px;';
        
        toast.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }
}

// Global function for refresh button
function refreshData() {
    if (window.reconciliation) {
        window.reconciliation.loadAllData();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.reconciliation = new ManualReconciliation();
});

// Export for global access
window.ManualReconciliation = ManualReconciliation; 