from django.urls import path
from .views import (
    UploadCSVView, 
    UploadFileView,
    UnmatchedTransactionsView, 
    MatchTransactionView, 
    ReconciliationLogsView,
    BulkReconciliationView,
    ReprocessTransactionView,
    ReconciliationStatsView,
    UnpaidInvoicesView,
    ManualReconciliationView,
    NotificationManagementView,
    PDFExportView,
    NotificationSettingsView
)

urlpatterns = [
    # File upload endpoints (new generic endpoint supports both CSV and Excel)
    path('bank/upload/', UploadFileView.as_view(), name='upload_file'),
    path('bank/upload/csv/', UploadCSVView.as_view(), name='upload_csv'),  # Backward compatibility
    
    # Transaction and reconciliation endpoints
    path('bank/unmatched/', UnmatchedTransactionsView.as_view(), name='unmatched_transactions'),
    path('bank/match/', MatchTransactionView.as_view(), name='match_transaction'),
    path('invoices/unpaid/', UnpaidInvoicesView.as_view(), name='unpaid_invoices'),
    path('admin/manual-reconciliation/', ManualReconciliationView.as_view(), name='manual_reconciliation'),
    path('reconciliation/logs/', ReconciliationLogsView.as_view(), name='reconciliation_logs'),
    path('reconciliation/bulk/', BulkReconciliationView.as_view(), name='bulk_reconciliation'),
    path('reconciliation/reprocess/', ReprocessTransactionView.as_view(), name='reprocess_transaction'),
    path('reconciliation/stats/', ReconciliationStatsView.as_view(), name='reconciliation_stats'),
    
    # Notification and export endpoints
    path('notifications/', NotificationManagementView.as_view(), name='notification_management'),
    path('notifications/settings/', NotificationSettingsView.as_view(), name='notification_settings'),
    path('export/pdf/', PDFExportView.as_view(), name='pdf_export'),
]