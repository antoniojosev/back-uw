from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.transaction.views import TransactionViewSet
from apps.transaction.views import TransactionCreateView, TransactionListView

app_name = 'transaction'

# Create a router and register our viewset with it
router = DefaultRouter()
router.register(r'', TransactionViewSet, basename='transaction')

urlpatterns = [
    # Keep the existing views for backward compatibility
    path('create/', TransactionCreateView.as_view(), name='create_transaction'),
    path('list/', TransactionListView.as_view(), name='list_transactions'),
    
    # Include the router URLs
    path('', include(router.urls)),
]