import csv
import io
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import BankTransaction, Invoice, Customer, ReconciliationLog
from .serializers import CSVUploadSerializer, BankTransactionSerializer
from django.db.models import Q

class UploadCSVView(APIView):
    def post(self, request):
        serializer = CSVUploadSerializer(data=request.data)
        if serializer.is_valid():
            csv_file = request.FILES['file']
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            for row in reader:
                transaction = BankTransaction.objects.create(
                    date=row['Date'],
                    description=row['Description'],
                    amount=row['Amount'],
                    reference_number=row['Reference Number'],
                )

                # Try auto-reconciliation
                invoice = Invoice.objects.filter(
                    Q(status='unpaid'),
                    Q(amount_due=transaction.amount),
                    Q(customer__name__icontains=transaction.description) |
                    Q(customer__name__icontains=transaction.reference_number)
                ).first()

                if invoice:
                    invoice.status = 'paid'
                    invoice.save()
                    transaction.status = 'matched'
                    transaction.save()
                    ReconciliationLog.objects.create(
                        transaction=transaction,
                        invoice=invoice,
                        matched_by='auto'
                    )
            return Response({'msg': 'Upload successful'}, status=status.HTTP_201_CREATED)
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
                matched_by='manual'
            )
            return Response({'msg': 'Matched manually'}, status=status.HTTP_200_OK)
        except:
            return Response({'error': 'Invalid IDs'}, status=status.HTTP_400_BAD_REQUEST)

class ReconciliationLogsView(APIView):
    def get(self, request):
        logs = ReconciliationLog.objects.all().select_related('transaction', 'invoice')
        data = [
            {
                "transaction_id": log.transaction.id,
                "invoice_id": log.invoice.id if log.invoice else None,
                "matched_by": log.matched_by,
                "timestamp": log.timestamp
            } for log in logs
        ]
        return Response(data)

