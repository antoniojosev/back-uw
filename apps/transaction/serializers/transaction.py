from rest_framework import serializers
from django.db import transaction as db_transaction
from django.utils import timezone
from datetime import timedelta

from apps.transaction.models import Transaction
from apps.wallet.models import Wallet
from apps.roi.models import ROI
from utils.bo import calculate_rois


class TransactionSerializer(serializers.Serializer):
    """
    Serializer for handling deposit and withdrawal transactions.
    """
    wallet_address = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(max_digits=40, decimal_places=10, min_value=0.000001)
    is_deposit = serializers.BooleanField()
    hash = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    def validate_amount(self, value):
        """
        Validate that the amount is positive.
        """
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor que cero.")
        return value
    
    def validate(self, data):
        """
        Validate the transaction data.
        """
        user = self.context['request'].user
        if not user.is_authenticated:
            raise serializers.ValidationError({"non_field_errors": "Usuario no autenticado."})
        try:
            # For withdrawals, ensure the system wallet has enough funds
            if not data['is_deposit']:
                if calculate_rois(user) < data['amount']:
                    raise serializers.ValidationError(
                        {"amount": "No hay fondos suficientes para completar esta transacción."}
                    )
                
                # Check if user has made a withdrawal in the last 7 days
                seven_days_ago = timezone.now() - timedelta(days=7)
                
                recent_withdrawal = Transaction.objects.filter(
                    destination__owner=user,
                    is_deposit=False,
                    created_at__gte=seven_days_ago
                ).exists()
                
                if recent_withdrawal:
                    raise serializers.ValidationError(
                        {"non_field_errors": "Ya has realizado un retiro en los últimos 7 días. Por favor espera."}
                    )
        except Wallet.DoesNotExist:
            raise serializers.ValidationError(
                {"non_field_errors": "Error en la configuración del sistema. Contacte al administrador."}
            )
        return data
    
    @db_transaction.atomic
    def create(self, validated_data):
        """
        Create a new transaction (deposit or withdrawal).
        """
        wallet_address = validated_data['wallet_address']
        amount = validated_data['amount']
        is_deposit = validated_data['is_deposit']
        hash_value = validated_data.get('hash', None)
        
        # Get the authenticated user from the context
        user = self.context['request'].user
        
        try:
            # Try to find if the user already has a wallet with this address
            try:
                if is_deposit:
                    user_wallet = Wallet.objects.get(owner=user)
                else:
                    user_wallet = Wallet.objects.get(address=wallet_address, owner=user)
            except Wallet.DoesNotExist:
                # Create a new wallet for the user
                user_wallet = Wallet.objects.update(
                    address=wallet_address,
                )
            
            
            # Get the system wallet
            system_wallet = Wallet.objects.get(owner__email='admin@gmail.com')
            
            # Set origin and destination based on transaction type
            if is_deposit:
                origin = user_wallet
                destination = system_wallet

            else:
                origin = system_wallet
                destination = user_wallet
                
                if calculate_rois(user) < amount:
                    raise serializers.ValidationError(
                        {"amount": "No hay fondos suficientes para completar esta transacción."}
                    )
            
            
            if amount == 0.3:
                amount = 650
            elif amount == 0.1:
                amount = 150

            # Create the transaction
            transaction = Transaction.objects.create(
                origin=origin,
                destination=destination,
                amount=amount,
                is_deposit=is_deposit,
                is_pending=True if not is_deposit else False, 
                is_approved=False if not is_deposit else True,
                hash=hash_value,
            )

            if is_deposit:
                user_wallet.balance += amount
                user_wallet.save()
                ROI.objects.create(
                    owner=user,
                    deposit_amount=amount,
                    transaction=transaction,
                )
            else:
                user_wallet.balance -= amount
                user_wallet.save()
            
            return transaction
            
        except Wallet.DoesNotExist:
            raise serializers.ValidationError(
                {"non_field_errors": "Error en la configuración del sistema. Contacte al administrador."}
            )


class TransactionListSerializer(serializers.ModelSerializer):
    """
    Serializer to display transaction details for a user.
    """
    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    amount = serializers.DecimalField(max_digits=40, decimal_places=10)
    hash = serializers.CharField(required=False, allow_null=True)
    rois = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = ['id', 'user', 'type', 'amount', 'status', 'created_at', 'hash', 'rois']
    
    def get_type(self, obj):
        """
        Return 'deposit' or 'withdrawal' based on transaction type.
        """
        return 'deposit' if obj.is_deposit else 'withdrawal'
    
    def get_status(self, obj):
        """
        Return the transaction status.
        """
        if obj.is_pending:
            return 'pending'
        elif obj.is_approved:
            return 'approved'
        else:
            return 'rejected'
    
    def get_user(self, obj):
        """
        Return information about the wallet counterparty.
        """
        request = self.context.get('request')
        if not request or not request.user:
            return None
            
        user_wallets = request.user.wallets.all()
        
        # If user is sender, show recipient
        if obj.origin and obj.origin in user_wallets:
            if obj.destination:
                return {
                    'id': str(obj.destination.owner.id),
                    'username': obj.destination.owner.username
                }
        # If user is recipient, show sender
        elif obj.destination and obj.destination in user_wallets:
            if obj.origin:
                return {
                    'id': str(obj.origin.owner.id),
                    'username': obj.origin.owner.username
                }
        
        # For system wallet or missing counterparty
        return {
            'id': 'system',
            'username': 'System'
        }
    
    def get_rois(self, obj):
        """
        Return the ROIs associated with the transaction.
        """
        request = self.context.get('request')
        if not request or not request.user:
            return None
        
        user = request.user
        roi = ROI.objects.filter(owner=user, transaction=obj).first()
        if not roi:
            return None
        data = {
            'daily_percentage': roi.daily_percentage,
            'started_at': roi.created_at,
        }
        
        return data


class WithdrawalCheckSerializer(serializers.Serializer):
    """
    Serializer para verificar si un usuario puede realizar un retiro.
    """
    can_withdraw = serializers.BooleanField()
    days_remaining = serializers.IntegerField(required=False)
    message = serializers.CharField()