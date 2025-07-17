from rest_framework import serializers
from .models import BankTransaction, Invoice

class BankTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankTransaction
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'

class CSVUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
