from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import models

from apps.transaction.models import Transaction
from apps.transaction.serializers import TransactionSerializer, TransactionListSerializer
from apps.transaction.views.legacy import AdminPermission, ClientTransactionPermission
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import action
from apps.transaction.serializers import WithdrawalCheckSerializer

class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transactions.
    """
    queryset = Transaction.objects.all().order_by('-created_at')
    serializer_class = TransactionListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            permission_classes = [ClientTransactionPermission]
        elif self.action in ['approve', 'reject']:
            permission_classes = [AdminPermission]
        else:
            # For list, retrieve, etc.
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'create':
            return TransactionSerializer
        return TransactionListSerializer
        
    def get_queryset(self):
        """
        This view should return a list of all transactions where the authenticated user
        is either the origin or destination.
        """
        user = self.request.user
        
        # Admin users can see all transactions
        if user.is_staff:
            return Transaction.objects.all().order_by('-created_at')
            
        # Regular users can only see their own transactions
        wallets = user.wallets.all()
        return Transaction.objects.filter(
            models.Q(origin__in=wallets) | models.Q(destination__in=wallets)
        ).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """
        Create a new transaction.
        """
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            transaction = serializer.save()
            transaction_data = TransactionListSerializer(transaction, context=self.get_serializer_context()).data
            return Response(transaction_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a pending transaction.
        """
        return self._process_transaction(request, pk, approve=True)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a pending transaction.
        """
        return self._process_transaction(request, pk, approve=False)
    
    def _process_transaction(self, request, pk, approve=True):
        """
        Helper method to process (approve or reject) a transaction.
        """
        transaction = get_object_or_404(Transaction, pk=pk)
        
        # Check if transaction is already processed
        if not transaction.is_pending:
            return Response(
                {"detail": "Transaction has already been processed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update the transaction
        transaction.is_pending = False
        transaction.is_approved = approve
        transaction.reviewer = request.user
        transaction.reviewed_at = timezone.now()
        transaction.save()
        
        # Update wallet balance if the transaction is approved and it's a withdrawal
        if approve and not transaction.is_deposit:
            destination_wallet = transaction.destination
            if destination_wallet:
                destination_wallet.last_transaction_date = timezone.now()
                destination_wallet.save()
        
        # Return the updated transaction
        transaction_data = TransactionListSerializer(transaction, context={'request': request}).data
        
        action_text = "approved" if approve else "rejected"
        return Response(
            {
                "detail": f"Transaction {action_text} successfully.",
                "transaction": transaction_data
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def check_withdrawal(self, request):
        """
        Verifica si el usuario puede realizar un retiro.
        """
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"message": "Usuario no autenticado"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Buscar el último retiro del usuario
        seven_days_ago = timezone.now() - timedelta(days=7)
        last_withdrawal = Transaction.objects.filter(
            destination__owner=user,
            is_deposit=False,
            created_at__gte=seven_days_ago
        ).order_by('-created_at').first()

        if last_withdrawal:
            # Calcular días restantes
            days_passed = (timezone.now() - last_withdrawal.created_at).days
            days_remaining = 7 - days_passed
            
            return Response(
                WithdrawalCheckSerializer({
                    'can_withdraw': False,
                    'days_remaining': days_remaining,
                    'message': f'Debes esperar {days_remaining} días para realizar otro retiro.'
                }).data
            )

        return Response(
            WithdrawalCheckSerializer({
                'can_withdraw': True,
                'message': 'Puedes realizar un retiro.'
            }).data
        )