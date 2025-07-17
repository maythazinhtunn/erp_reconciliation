from django.core.management.base import BaseCommand
from reconciliation.models import Customer, Invoice, BankTransaction
from decimal import Decimal
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Populate sample data for testing reconciliation functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new samples',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            BankTransaction.objects.all().delete()
            Invoice.objects.all().delete()
            Customer.objects.all().delete()

        # Create sample customers
        customers_data = [
            {'name': 'Acme Corporation', 'email': 'billing@acme.com'},
            {'name': 'TechStart Inc', 'email': 'accounts@techstart.com'},
            {'name': 'Global Manufacturing', 'email': 'finance@global-mfg.com'},
            {'name': 'Local Services LLC', 'email': 'payments@localservices.com'},
            {'name': 'Digital Solutions', 'email': 'billing@digitalsol.com'},
        ]

        customers = []
        for customer_data in customers_data:
            customer, created = Customer.objects.get_or_create(**customer_data)
            customers.append(customer)
            if created:
                self.stdout.write(f'Created customer: {customer.name}')

        # Create sample invoices
        invoices_data = [
            {'customer': customers[0], 'amount_due': Decimal('1500.00'), 'reference_number': 'INV-001'},
            {'customer': customers[1], 'amount_due': Decimal('2750.50'), 'reference_number': 'INV-002'},
            {'customer': customers[2], 'amount_due': Decimal('5000.00'), 'reference_number': 'INV-003'},
            {'customer': customers[3], 'amount_due': Decimal('850.75'), 'reference_number': 'INV-004'},
            {'customer': customers[4], 'amount_due': Decimal('1200.00'), 'reference_number': 'INV-005'},
            {'customer': customers[0], 'amount_due': Decimal('3200.25'), 'reference_number': 'INV-006'},
            {'customer': customers[2], 'amount_due': Decimal('750.00'), 'reference_number': 'INV-007'},
        ]

        invoices = []
        for invoice_data in invoices_data:
            invoice, created = Invoice.objects.get_or_create(**invoice_data)
            invoices.append(invoice)
            if created:
                self.stdout.write(f'Created invoice: {invoice.reference_number} for {invoice.customer.name}')

        # Create sample bank transactions
        base_date = date.today() - timedelta(days=30)
        
        transactions_data = [
            # Perfect matches
            {
                'date': base_date + timedelta(days=1),
                'description': 'Payment from Acme Corporation for services',
                'amount': Decimal('1500.00'),
                'reference_number': 'INV-001'
            },
            {
                'date': base_date + timedelta(days=2),
                'description': 'TechStart Inc payment ref INV-002',
                'amount': Decimal('2750.50'),
                'reference_number': 'TECH-PAY-001'
            },
            # Amount matches but different reference
            {
                'date': base_date + timedelta(days=3),
                'description': 'Global Manufacturing payment for invoice',
                'amount': Decimal('5000.00'),
                'reference_number': 'GM-WIRE-001'
            },
            # Customer name in description
            {
                'date': base_date + timedelta(days=4),
                'description': 'Transfer from Local Services LLC',
                'amount': Decimal('850.75'),
                'reference_number': 'BANK-TRF-123'
            },
            # Partial customer name match
            {
                'date': base_date + timedelta(days=5),
                'description': 'Payment from Digital Solutions dept',
                'amount': Decimal('1200.00'),
                'reference_number': 'DS-PAY-456'
            },
            # Amount only match (lower confidence)
            {
                'date': base_date + timedelta(days=6),
                'description': 'Wire transfer incoming',
                'amount': Decimal('3200.25'),
                'reference_number': 'WIRE-789'
            },
            # No clear match
            {
                'date': base_date + timedelta(days=7),
                'description': 'Unknown deposit',
                'amount': Decimal('999.99'),
                'reference_number': 'UNK-001'
            },
            # Another perfect match
            {
                'date': base_date + timedelta(days=8),
                'description': 'Payment for INV-007 from Global Manufacturing',
                'amount': Decimal('750.00'),
                'reference_number': 'INV-007'
            },
        ]

        for transaction_data in transactions_data:
            transaction, created = BankTransaction.objects.get_or_create(**transaction_data)
            if created:
                self.stdout.write(f'Created transaction: {transaction.reference_number} - ${transaction.amount}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample data:\n'
                f'- {len(customers)} customers\n'
                f'- {len(invoices)} invoices\n'
                f'- {len(transactions_data)} bank transactions\n\n'
                f'You can now test reconciliation by:\n'
                f'1. Running bulk reconciliation\n'
                f'2. Uploading the bank_trans.csv file\n'
                f'3. Using the API endpoints to match transactions'
            )
        ) 