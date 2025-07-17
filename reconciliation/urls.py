from django.urls import path
from .views import (
    UploadCSVView, 
    UnmatchedTransactionsView, 
    MatchTransactionView, 
    ReconciliationLogsView,
    BulkReconciliationView,
    ReprocessTransactionView,
    ReconciliationStatsView,
    UnpaidInvoicesView,
    ManualReconciliationView
)

urlpatterns = [
    path('bank/upload/', UploadCSVView.as_view(), name='upload_csv'),
    path('bank/unmatched/', UnmatchedTransactionsView.as_view(), name='unmatched_transactions'),
    path('bank/match/', MatchTransactionView.as_view(), name='match_transaction'),
    path('invoices/unpaid/', UnpaidInvoicesView.as_view(), name='unpaid_invoices'),
    path('admin/manual-reconciliation/', ManualReconciliationView.as_view(), name='manual_reconciliation'),
    path('reconciliation/logs/', ReconciliationLogsView.as_view(), name='reconciliation_logs'),
    path('reconciliation/bulk/', BulkReconciliationView.as_view(), name='bulk_reconciliation'),
    path('reconciliation/reprocess/', ReprocessTransactionView.as_view(), name='reprocess_transaction'),
    path('reconciliation/stats/', ReconciliationStatsView.as_view(), name='reconciliation_stats'),
]