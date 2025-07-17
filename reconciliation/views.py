import csv
import io
import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import BankTransaction, Invoice, Customer, ReconciliationLog, NotificationLog
from .serializers import FileUploadSerializer, BankTransactionSerializer, InvoiceSerializer
from .services import ReconciliationService, NotificationService, PDFExportService
from django.db.models import Q
from django.http import JsonResponse
from datetime import datetime

class UploadFileView(APIView):
    """
    Upload CSV or Excel files containing bank transaction data.
    Supports .csv, .xlsx, and .xls formats.
    """
    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            uploaded_file = request.FILES['file']
            
            try:
                # Determine file type and read accordingly
                file_extension = uploaded_file.name.lower().split('.')[-1]
                
                if file_extension == 'csv':
                    # Read CSV file
                    df = pd.read_csv(uploaded_file)
                elif file_extension in ['xlsx', 'xls']:
                    # Read Excel file
                    df = pd.read_excel(uploaded_file)
                else:
                    return Response({
                        'error': f'Unsupported file format: {file_extension}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Validate required columns
                required_columns = ['Date', 'Description', 'Amount', 'Reference Number']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    return Response({
                        'error': f'Missing required columns: {", ".join(missing_columns)}',
                        'required_columns': required_columns,
                        'found_columns': list(df.columns)
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Process the data
                uploaded_transactions = []
                reconciliation_results = []
                errors = []
                
                for index, row in df.iterrows():
                    try:
                        # Create transaction from row data
                        transaction = BankTransaction.objects.create(
                            date=row['Date'],
                            description=str(row['Description']),
                            amount=row['Amount'],
                            reference_number=str(row['Reference Number']) if pd.notna(row['Reference Number']) else '',
                        )
                        uploaded_transactions.append(transaction)

                        # Use the sophisticated ReconciliationService for automatic reconciliation
                        result = ReconciliationService.process_transaction_reconciliation(transaction)
                        reconciliation_results.append({
                            'transaction_id': transaction.id,
                            'result': result
                        })
                    except Exception as e:
                        errors.append({
                            'row': index + 1,
                            'error': str(e)
                        })
                        continue

                # Check for unmatched transactions and send notification if needed
                unmatched_count = BankTransaction.objects.filter(status='unmatched').count()
                notification_result = NotificationService.send_unmatched_transactions_notification()

                response_data = {
                    'msg': 'Upload successful',
                    'file_type': file_extension.upper(),
                    'uploaded_count': len(uploaded_transactions),
                    'reconciliation_results': reconciliation_results
                }
                
                if errors:
                    response_data['errors'] = errors
                    response_data['error_count'] = len(errors)
                
                if notification_result.get('sent'):
                    response_data['notification_sent'] = True
                    response_data['notification_details'] = notification_result

                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': f'Failed to process file: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Keep the old class name for backward compatibility
UploadCSVView = UploadFileView

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

class UnpaidInvoicesView(APIView):
    """
    API endpoint to get all unpaid invoices
    """
    def get(self, request):
        unpaid_invoices = Invoice.objects.filter(status='unpaid').select_related('customer')
        serializer = InvoiceSerializer(unpaid_invoices, many=True)
        return Response(serializer.data)


class NotificationManagementView(APIView):
    """
    API endpoint to manage notifications for unmatched transactions
    """
    
    def post(self, request):
        """Send notification for unmatched transactions manually"""
        result = NotificationService.send_unmatched_transactions_notification()
        
        if result['success']:
            return Response({
                'msg': 'Notification sent successfully',
                'details': result
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Failed to send notification',
                'details': result
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        """Get notification history"""
        notifications = NotificationLog.objects.all().order_by('-timestamp')[:20]
        
        data = [
            {
                'id': notification.id,
                'type': notification.notification_type,
                'recipients': notification.recipients,
                'unmatched_count': notification.unmatched_count,
                'total_transactions': notification.total_transactions,
                'timestamp': notification.timestamp,
                'success': notification.success,
                'error_message': notification.error_message
            } for notification in notifications
        ]
        
        return Response({
            'notifications': data,
            'total_count': NotificationLog.objects.count()
        })


class PDFExportView(APIView):
    """
    API endpoint to export reconciliation summary as PDF
    """
    
    def get(self, request):
        """Generate and return PDF reconciliation summary"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Validate dates if provided
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            pdf_response = PDFExportService.generate_reconciliation_summary_pdf(start_date, end_date)
            return pdf_response
        except Exception as e:
            return Response(
                {'error': f'Failed to generate PDF: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotificationSettingsView(APIView):
    """
    API endpoint to manage notification settings
    """
    
    def get(self, request):
        """Get current notification settings"""
        from django.conf import settings
        
        notification_settings = getattr(settings, 'NOTIFICATION_SETTINGS', {})
        
        return Response({
            'settings': notification_settings,
            'unmatched_count': BankTransaction.objects.filter(status='unmatched').count()
        })
    
    def post(self, request):
        """Test notification system"""
        # This endpoint can be used to test if notifications are working
        test_result = NotificationService.check_and_send_unmatched_notification()
        
        return Response({
            'test_result': test_result,
            'current_unmatched': BankTransaction.objects.filter(status='unmatched').count()
        })

class ManualReconciliationView(View):
    """
    Template view for the manual reconciliation admin page
    """
    def get(self, request):
        return render(request, 'reconciliation/manual_reconciliation.html')

