from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.transaction.views import TransactionViewSet
from apps.transaction.views import TransactionCreateView, TransactionListView

app_name = 'transaction_v2'

# Create a router and register our viewset with it
router = DefaultRouter()
router.register(r'', TransactionViewSet, basename='transaction_v2')

urlpatterns = [
    path('', include(router.urls)),
]