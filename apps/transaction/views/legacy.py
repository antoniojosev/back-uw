from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

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
        
        return request.user.is_active and not request.user.is_staff


class AdminPermission(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """
    def has_permission(self, request, view):
        # Only authenticated users who are staff can access
        return request.user.is_authenticated and request.user.is_staff


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
            
            transaction_data = TransactionListSerializer(transaction, context=self.get_serializer_context()).data
            
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


class TransactionApprovalView(APIView):
    """
    API endpoint that allows admin users to approve or reject transactions.
    """
    permission_classes = [AdminPermission]
    
    def post(self, request, transaction_id):
        """
        Approve or reject a transaction based on the action parameter.
        Required parameters:
        - action: 'approve' or 'reject'
        """
        # Get the transaction
        transaction = get_object_or_404(Transaction, id=transaction_id)
        
        # Check if transaction is already processed
        if not transaction.is_pending:
            return Response(
                {"detail": "Transaction has already been processed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the action (approve or reject)
        action = request.data.get('action')
        
        if action not in ['approve', 'reject']:
            return Response(
                {"detail": "Invalid action. Must be 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update the transaction
        transaction.is_pending = False
        transaction.is_approved = action == 'approve'
        transaction.reviewer = request.user
        transaction.reviewed_at = timezone.now()
        transaction.save()
        
        # Update wallet balance if the transaction is approved and it's a withdrawal
        if action == 'approve' and not transaction.is_deposit:
            destination_wallet = transaction.destination
            if destination_wallet:
                destination_wallet.last_transaction_date = timezone.now()
                destination_wallet.save()
        
        # Return the updated transaction
        transaction_data = TransactionListSerializer(transaction, context={'request': request}).data
        
        return Response(
            {
                "detail": f"Transaction {action}d successfully.",
                "transaction": transaction_data
            },
            status=status.HTTP_200_OK
        )