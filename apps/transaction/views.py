from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.transaction.serializers import TransactionSerializer, TransactionListSerializer
from apps.transaction.models import Transaction
from django.db import models

class ClientTransactionPermission(permissions.BasePermission):
    """
    Custom permission to only allow clients to create transactions.
    """
    def has_permission(self, request, view):
        # Only authenticated users can access
        if not request.user.is_authenticated:
            return False
        
        # Check if the user has the client role
        print(not request.user.is_staff)
        return request.user.is_active and not request.user.is_staff


class TransactionCreateView(generics.CreateAPIView):
    """
    API endpoint that allows clients to create transactions (deposits or withdrawals).
    """
    serializer_class = TransactionSerializer
    permission_classes = [ClientTransactionPermission]
    
    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        context = super().get_serializer_context()
        return context
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            transaction = serializer.save()
            
            transaction_data = TransactionListSerializer(transaction).data
            
            return Response(transaction_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionListView(generics.ListAPIView):
    """
    API endpoint that lists transactions where the authenticated user is either the origin or destination.
    """
    serializer_class = TransactionListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        This view should return a list of all transactions where the authenticated user
        is either the origin or destination.
        """
        user = self.request.user
        # Get the user's wallet(s)
        wallets = user.wallets.all()
        # Get transactions where user's wallet is origin or destination
        return Transaction.objects.filter(
            models.Q(origin__in=wallets) | models.Q(destination__in=wallets)
        ).order_by('-created_at')
