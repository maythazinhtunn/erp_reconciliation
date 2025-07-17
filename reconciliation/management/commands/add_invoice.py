from django.core.management.base import BaseCommand
from reconciliation.models import Customer, Invoice
from decimal import Decimal, InvalidOperation

class Command(BaseCommand):
    help = 'Add a single invoice record to the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--customer-name',
            type=str,
            help='Customer name (if not provided, will prompt or use default)',
        )
        parser.add_argument(
            '--customer-email',
            type=str,
            help='Customer email (if not provided, will prompt or use default)',
        )
        parser.add_argument(
            '--amount',
            type=str,
            help='Invoice amount (if not provided, will prompt or use default)',
        )
        parser.add_argument(
            '--reference',
            type=str,
            help='Reference number (optional)',
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['unpaid', 'paid'],
            default='unpaid',
            help='Invoice status (default: unpaid)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Adding a new invoice record...\n')

        # Get or create customer
        customer_name = options.get('customer_name')
        customer_email = options.get('customer_email')
        
        if not customer_name:
            customer_name = input('Enter customer name (default: "Sample Customer"): ').strip()
            if not customer_name:
                customer_name = "Sample Customer"
        
        if not customer_email:
            customer_email = input('Enter customer email (default: "sample@example.com"): ').strip()
            if not customer_email:
                customer_email = "sample@example.com"

        # Get or create the customer
        customer, created = Customer.objects.get_or_create(
            name=customer_name,
            defaults={'email': customer_email}
        )
        
        if created:
            self.stdout.write(f'Created new customer: {customer.name}')
        else:
            self.stdout.write(f'Using existing customer: {customer.name}')

        # Get invoice amount
        amount = options.get('amount')
        if not amount:
            amount = input('Enter invoice amount (default: "1000.00"): ').strip()
            if not amount:
                amount = "1000.00"

        try:
            amount_decimal = Decimal(amount)
            if amount_decimal <= 0:
                raise ValueError("Amount must be positive")
        except (InvalidOperation, ValueError) as e:
            self.stdout.write(
                self.style.ERROR(f'Invalid amount "{amount}": {e}')
            )
            return

        # Get reference number
        reference_number = options.get('reference')
        if not reference_number:
            reference_number = input('Enter reference number (optional): ').strip()
            if not reference_number:
                reference_number = None

        # Get status
        status = options.get('status', 'unpaid')

        # Create the invoice
        try:
            invoice = Invoice.objects.create(
                customer=customer,
                amount_due=amount_decimal,
                reference_number=reference_number,
                status=status
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully created invoice:\n'
                    f'- ID: {invoice.id}\n'
                    f'- Customer: {invoice.customer.name}\n'
                    f'- Amount: ${invoice.amount_due}\n'
                    f'- Reference: {invoice.reference_number or "None"}\n'
                    f'- Status: {invoice.status}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating invoice: {e}')
            ) 