from django.db import models

# Create your models here.
from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

class Invoice(models.Model):
    STATUS = [('unpaid', 'Unpaid'), ('paid', 'Paid')]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS, default='unpaid')

class BankTransaction(models.Model):
    STATUS = [('matched', 'Matched'), ('unmatched', 'Unmatched')]
    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=STATUS, default='unmatched')

class ReconciliationLog(models.Model):
    transaction = models.ForeignKey(BankTransaction, on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True, blank=True)
    matched_by = models.CharField(max_length=10, choices=[('auto', 'Auto'), ('manual', 'Manual')])
    timestamp = models.DateTimeField(auto_now_add=True)
