from django.db import models

# Create your models here.
from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

    def __str__(self):
        return self.name

class Invoice(models.Model):
    STATUS = [('unpaid', 'Unpaid'), ('paid', 'Paid')]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS, default='unpaid')
    reference_number = models.CharField(max_length=100, blank=True, null=True)  # Added for matching

    def __str__(self):
        return f"Invoice {self.id} - {self.customer.name} - ${self.amount_due}"

class BankTransaction(models.Model):
    STATUS = [('matched', 'Matched'), ('unmatched', 'Unmatched')]
    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=STATUS, default='unmatched')

    def __str__(self):
        return f"Transaction {self.id} - ${self.amount} - {self.status}"

class ReconciliationLog(models.Model):
    transaction = models.ForeignKey(BankTransaction, on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True, blank=True)
    matched_by = models.CharField(max_length=10, choices=[('auto', 'Auto'), ('manual', 'Manual')])
    timestamp = models.DateTimeField(auto_now_add=True)
    match_reason = models.CharField(max_length=255, blank=True, null=True)  # Added for detailed logging
    confidence_score = models.FloatField(default=0.0)  # Added for confidence tracking

    def __str__(self):
        return f"Log {self.id} - Transaction {self.transaction.id} - {self.matched_by}"

class NotificationLog(models.Model):
    """Model to track sent notifications"""
    NOTIFICATION_TYPES = [
        ('unmatched_transactions', 'Unmatched Transactions'),
        ('reconciliation_summary', 'Reconciliation Summary'),
    ]
    
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    recipients = models.TextField()  # Store email addresses as comma-separated
    unmatched_count = models.IntegerField(default=0)
    total_transactions = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Notification {self.id} - {self.notification_type} - {self.timestamp}"
