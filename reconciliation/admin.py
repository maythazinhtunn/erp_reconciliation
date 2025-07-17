from django.contrib import admin
from .models import Customer, Invoice, BankTransaction, ReconciliationLog, NotificationLog

# Register your models here.
admin.site.register(Customer)
admin.site.register(Invoice)
admin.site.register(BankTransaction)
admin.site.register(ReconciliationLog)

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'notification_type', 'unmatched_count', 'success', 'timestamp']
    list_filter = ['notification_type', 'success', 'timestamp']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
