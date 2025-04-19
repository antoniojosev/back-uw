from django.urls import path
from apps.transaction.views import TransactionCreateView, TransactionListView

app_name = 'transaction'

urlpatterns = [
    path('create/', TransactionCreateView.as_view(), name='create_transaction'),
    path('list/', TransactionListView.as_view(), name='list_transactions'),
]