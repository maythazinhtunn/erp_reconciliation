from django.core.management.base import BaseCommand
from reconciliation.models import BankTransaction, Invoice, ReconciliationLog
from reconciliation.services import ReconciliationService

class Command(BaseCommand):
    help = 'Test the reconciliation functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--transaction-id',
            type=int,
            help='Test reconciliation for a specific transaction ID',
        )
        parser.add_argument(
            '--bulk',
            action='store_true',
            help='Test bulk reconciliation for all unmatched transactions',
        )

    def handle(self, *args, **options):
        self.stdout.write('=== Reconciliation Testing ===\n')

        if options['transaction_id']:
            # Test specific transaction
            try:
                transaction = BankTransaction.objects.get(id=options['transaction_id'])
                self.test_single_transaction(transaction)
            except BankTransaction.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Transaction with ID {options["transaction_id"]} not found')
                )
        elif options['bulk']:
            # Test bulk reconciliation
            self.test_bulk_reconciliation()
        else:
            # Test all unmatched transactions individually
            self.test_all_transactions()

    def test_single_transaction(self, transaction):
        self.stdout.write(f'Testing reconciliation for transaction {transaction.id}:')
        self.stdout.write(f'  Amount: ${transaction.amount}')
        self.stdout.write(f'  Description: {transaction.description}')
        self.stdout.write(f'  Reference: {transaction.reference_number}')
        self.stdout.write(f'  Current Status: {transaction.status}\n')

        # Show potential matches before reconciliation
        match_result = ReconciliationService._find_matching_invoice_with_confidence(transaction)
        
        self.stdout.write('Potential match analysis:')
        if match_result['invoice']:
            invoice = match_result['invoice']
            self.stdout.write(f'  Best Match: Invoice {invoice.id} - {invoice.customer.name}')
            self.stdout.write(f'  Invoice Amount: ${invoice.amount_due}')
            self.stdout.write(f'  Confidence: {match_result["confidence"]:.2f}')
            self.stdout.write(f'  Reason: {match_result["reason"]}')
        else:
            self.stdout.write('  No potential matches found')

        # Perform reconciliation
        result = ReconciliationService.process_transaction_reconciliation(transaction)
        
        self.stdout.write(f'\nReconciliation Result:')
        self.stdout.write(f'  Status: {result["status"]}')
        self.stdout.write(f'  Confidence: {result["confidence_score"]:.2f}')
        self.stdout.write(f'  Reason: {result["match_reason"]}')
        
        if result['invoice_id']:
            self.stdout.write(f'  Matched Invoice ID: {result["invoice_id"]}')
            
        self.stdout.write(f'  Log Entry ID: {result["log_id"]}\n')

    def test_bulk_reconciliation(self):
        unmatched_count = BankTransaction.objects.filter(status='unmatched').count()
        self.stdout.write(f'Found {unmatched_count} unmatched transactions for bulk reconciliation\n')

        if unmatched_count == 0:
            self.stdout.write('No unmatched transactions to process.')
            return

        # Perform bulk reconciliation
        results = ReconciliationService.bulk_reconcile_transactions()
        
        self.stdout.write('Bulk Reconciliation Results:')
        self.stdout.write(f'  Total Processed: {results["total_processed"]}')
        self.stdout.write(f'  Matched: {results["matched"]}')
        self.stdout.write(f'  Unmatched: {results["unmatched"]}')
        self.stdout.write(f'  High Confidence Matches: {results["high_confidence_matches"]}')
        self.stdout.write(f'  Low Confidence Matches: {results["low_confidence_matches"]}\n')

        # Show details for each transaction
        for detail in results['details']:
            self.stdout.write(f'Transaction {detail["transaction_id"]}:')
            self.stdout.write(f'  Amount: ${detail["amount"]}')
            self.stdout.write(f'  Description: {detail["description"][:50]}...')
            self.stdout.write(f'  Result: {detail["result"]["status"]}')
            self.stdout.write(f'  Confidence: {detail["result"]["confidence_score"]:.2f}')
            if detail["result"]["invoice_id"]:
                self.stdout.write(f'  Matched Invoice: {detail["result"]["invoice_id"]}')
            self.stdout.write('')

    def test_all_transactions(self):
        unmatched_transactions = BankTransaction.objects.filter(status='unmatched')
        
        if not unmatched_transactions.exists():
            self.stdout.write('No unmatched transactions found.')
            return

        self.stdout.write(f'Testing reconciliation for {unmatched_transactions.count()} unmatched transactions:\n')

        for transaction in unmatched_transactions:
            self.test_single_transaction(transaction)
            self.stdout.write('-' * 50 + '\n')

        # Show summary
        self.show_reconciliation_summary()

    def show_reconciliation_summary(self):
        total_transactions = BankTransaction.objects.count()
        matched_transactions = BankTransaction.objects.filter(status='matched').count()
        unmatched_transactions = BankTransaction.objects.filter(status='unmatched').count()
        
        total_invoices = Invoice.objects.count()
        paid_invoices = Invoice.objects.filter(status='paid').count()
        unpaid_invoices = Invoice.objects.filter(status='unpaid').count()
        
        auto_matches = ReconciliationLog.objects.filter(matched_by='auto').count()
        manual_matches = ReconciliationLog.objects.filter(matched_by='manual').count()
        high_confidence = ReconciliationLog.objects.filter(confidence_score__gte=0.8).count()

        self.stdout.write(self.style.SUCCESS('=== RECONCILIATION SUMMARY ==='))
        self.stdout.write(f'Transactions: {matched_transactions}/{total_transactions} matched ({(matched_transactions/total_transactions*100):.1f}%)')
        self.stdout.write(f'Invoices: {paid_invoices}/{total_invoices} paid ({(paid_invoices/total_invoices*100):.1f}%)')
        self.stdout.write(f'Auto Matches: {auto_matches}')
        self.stdout.write(f'Manual Matches: {manual_matches}')
        self.stdout.write(f'High Confidence Matches: {high_confidence}')
        self.stdout.write(f'Unmatched Transactions: {unmatched_transactions}') 