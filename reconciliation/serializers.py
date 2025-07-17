from rest_framework import serializers
from .models import BankTransaction, Invoice, Customer, ReconciliationLog

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class BankTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankTransaction
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    
    class Meta:
        model = Invoice
        fields = '__all__'

class ReconciliationLogSerializer(serializers.ModelSerializer):
    transaction_amount = serializers.DecimalField(source='transaction.amount', max_digits=10, decimal_places=2, read_only=True)
    transaction_description = serializers.CharField(source='transaction.description', read_only=True)
    transaction_reference = serializers.CharField(source='transaction.reference_number', read_only=True)
    invoice_customer_name = serializers.CharField(source='invoice.customer.name', read_only=True)
    invoice_amount = serializers.DecimalField(source='invoice.amount_due', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ReconciliationLog
        fields = '__all__'

class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    
    def validate_file(self, value):
        """Validate that the uploaded file is either CSV or Excel format"""
        if not value.name:
            raise serializers.ValidationError("File name is required")
        
        # Get file extension
        file_extension = value.name.lower().split('.')[-1]
        
        # Check if it's a supported format
        supported_formats = ['csv', 'xlsx', 'xls']
        if file_extension not in supported_formats:
            raise serializers.ValidationError(
                f"Unsupported file format. Supported formats: {', '.join(supported_formats)}"
            )
        
        return value

# Keep the old name for backward compatibility
CSVUploadSerializer = FileUploadSerializer

class BulkReconciliationSerializer(serializers.Serializer):
    transaction_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of transaction IDs to reconcile. If not provided, all unmatched transactions will be processed."
    )

class TransactionMatchSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField()
    invoice_id = serializers.IntegerField()

class ReprocessTransactionSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField()
