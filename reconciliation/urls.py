from django.urls import path
from .views import UploadCSVView, UnmatchedTransactionsView, MatchTransactionView, ReconciliationLogsView

urlpatterns = [
    path('bank/upload/', UploadCSVView.as_view()),
    path('bank/unmatched/', UnmatchedTransactionsView.as_view()),
    path('bank/match/', MatchTransactionView.as_view()),
    path('reconciliation/logs/', ReconciliationLogsView.as_view()),
]