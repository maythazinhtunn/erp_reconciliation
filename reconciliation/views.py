import csv
import io
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import BankTransaction, Invoice, Customer, ReconciliationLog
from .serializers import CSVUploadSerializer, BankTransactionSerializer
from .services import ReconciliationService
from django.db.models import Q

class UploadCSVView(APIView):
    def post(self, request):
        serializer = CSVUploadSerializer(data=request.data)
        if serializer.is_valid():
            csv_file = request.FILES['file']
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            uploaded_transactions = []
            reconciliation_results = []

            for row in reader:
                transaction = BankTransaction.objects.create(
                    date=row['Date'],
                    description=row['Description'],
                    amount=row['Amount'],
                    reference_number=row['Reference Number'],
                )
                uploaded_transactions.append(transaction)

                # Use the sophisticated ReconciliationService for automatic reconciliation
                result = ReconciliationService.process_transaction_reconciliation(transaction)
                reconciliation_results.append({
                    'transaction_id': transaction.id,
                    'result': result
                })

            return Response({
                'msg': 'Upload successful',
                'uploaded_count': len(uploaded_transactions),
                'reconciliation_results': reconciliation_results
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UnmatchedTransactionsView(APIView):
    def get(self, request):
        unmatched = BankTransaction.objects.filter(status='unmatched')
        serializer = BankTransactionSerializer(unmatched, many=True)
        return Response(serializer.data)

class MatchTransactionView(APIView):
    def post(self, request):
        transaction_id = request.data.get('transaction_id')
        invoice_id = request.data.get('invoice_id')

        try:
            transaction = BankTransaction.objects.get(id=transaction_id)
            invoice = Invoice.objects.get(id=invoice_id)

            invoice.status = 'paid'
            invoice.save()

            transaction.status = 'matched'
            transaction.save()

            ReconciliationLog.objects.create(
                transaction=transaction,
                invoice=invoice,
                matched_by='manual',
                match_reason='Manual match by user',
                confidence_score=1.0
            )
            return Response({'msg': 'Matched manually'}, status=status.HTTP_200_OK)
        except:
            return Response({'error': 'Invalid IDs'}, status=status.HTTP_400_BAD_REQUEST)

class ReconciliationLogsView(APIView):
    def get(self, request):
        logs = ReconciliationLog.objects.all().select_related('transaction', 'invoice').order_by('-timestamp')
        data = [
            {
                "id": log.id,
                "transaction_id": log.transaction.id,
                "transaction_amount": str(log.transaction.amount),
                "transaction_description": log.transaction.description,
                "transaction_reference": log.transaction.reference_number,
                "invoice_id": log.invoice.id if log.invoice else None,
                "invoice_customer": log.invoice.customer.name if log.invoice else None,
                "matched_by": log.matched_by,
                "match_reason": log.match_reason,
                "confidence_score": log.confidence_score,
                "timestamp": log.timestamp
            } for log in logs
        ]
        return Response(data)

class BulkReconciliationView(APIView):
    """
    New endpoint for bulk reconciliation of unmatched transactions
    """
    def post(self, request):
        # Get all unmatched transactions or specific ones if provided
        transaction_ids = request.data.get('transaction_ids')
        
        if transaction_ids:
            transactions = BankTransaction.objects.filter(
                id__in=transaction_ids, 
                status='unmatched'
            )
        else:
            transactions = BankTransaction.objects.filter(status='unmatched')
        
        # Perform bulk reconciliation using the service
        results = ReconciliationService.bulk_reconcile_transactions(transactions)
        
        return Response({
            'msg': 'Bulk reconciliation completed',
            'summary': {
                'total_processed': results['total_processed'],
                'matched': results['matched'],
                'unmatched': results['unmatched'],
                'high_confidence_matches': results['high_confidence_matches'],
                'low_confidence_matches': results['low_confidence_matches']
            },
            'details': results['details']
        }, status=status.HTTP_200_OK)

class ReprocessTransactionView(APIView):
    """
    New endpoint to reprocess a specific transaction for reconciliation
    """
    def post(self, request):
        transaction_id = request.data.get('transaction_id')
        
        try:
            transaction = BankTransaction.objects.get(id=transaction_id)
            
            # Reset transaction status if needed
            if transaction.status == 'matched':
                # Find and reset the previously matched invoice
                previous_log = ReconciliationLog.objects.filter(
                    transaction=transaction
                ).exclude(invoice=None).first()
                
                if previous_log and previous_log.invoice:
                    previous_log.invoice.status = 'unpaid'
                    previous_log.invoice.save()
            
            transaction.status = 'unmatched'
            transaction.save()
            
            # Reprocess reconciliation
            result = ReconciliationService.process_transaction_reconciliation(transaction)
            
            return Response({
                'msg': 'Transaction reprocessed successfully',
                'transaction_id': transaction.id,
                'result': result
            }, status=status.HTTP_200_OK)
            
        except BankTransaction.DoesNotExist:
            return Response(
                {'error': 'Transaction not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class ReconciliationStatsView(APIView):
    """
    New endpoint to get reconciliation statistics
    """
    def get(self, request):
        total_transactions = BankTransaction.objects.count()
        matched_transactions = BankTransaction.objects.filter(status='matched').count()
        unmatched_transactions = BankTransaction.objects.filter(status='unmatched').count()
        
        total_invoices = Invoice.objects.count()
        paid_invoices = Invoice.objects.filter(status='paid').count()
        unpaid_invoices = Invoice.objects.filter(status='unpaid').count()
        
        auto_matches = ReconciliationLog.objects.filter(matched_by='auto').count()
        manual_matches = ReconciliationLog.objects.filter(matched_by='manual').count()
        
        high_confidence_matches = ReconciliationLog.objects.filter(
            confidence_score__gte=0.8
        ).count()
        
        return Response({
            'transactions': {
                'total': total_transactions,
                'matched': matched_transactions,
                'unmatched': unmatched_transactions,
                'match_rate': round((matched_transactions / total_transactions * 100), 2) if total_transactions > 0 else 0
            },
            'invoices': {
                'total': total_invoices,
                'paid': paid_invoices,
                'unpaid': unpaid_invoices,
                'payment_rate': round((paid_invoices / total_invoices * 100), 2) if total_invoices > 0 else 0
            },
            'reconciliation': {
                'auto_matches': auto_matches,
                'manual_matches': manual_matches,
                'high_confidence_matches': high_confidence_matches,
                'total_logs': auto_matches + manual_matches
            }
        })

