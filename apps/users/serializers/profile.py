from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import models
from apps.roi.models import ROI
from apps.transaction.models import Transaction
from apps.transaction.serializers.transaction import TransactionListSerializer
from utils.bo import calculate_rois, calculate_rois_by_date
from django.utils import timezone
from datetime import datetime
from decimal import Decimal

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    User profile serializer with specific fields requested.
    """
    walletAddress = serializers.CharField(read_only=True, required=False)  # Not in model
    balance = serializers.SerializerMethodField(read_only=True, required=False)  # Not in model
    isAdmin = serializers.SerializerMethodField()
    rois = serializers.SerializerMethodField()
    dailySummary = serializers.SerializerMethodField(read_only=True, required=False)  # Resumen diario


    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'walletAddress', 'balance', 'isAdmin', 'rois', 'dailySummary']
        read_only_fields = ['id', 'email', 'name', 'isAdmin', 'rois', 'dailySummary']

    def get_balance(self, obj):
        """
        Return the user's balance.
        """
        balance_total = calculate_rois(obj)
        if balance_total < 0:
            return 0.00
        return balance_total

    def get_isAdmin(self, obj):
        """
        Return whether the user is an admin.
        """
        return obj.is_staff
    
    def get_rois(self, obj):
        """
        Return the total ROI for the user.
        """
        rois = ROI.objects.filter(owner=obj)
        data = []
        for roi in rois:
            if roi.time_remaining.total_seconds() >= 0:
                data.append({
                    'started_at': roi.created_at,
                    'daily_percentage': roi.daily_percentage,
                    'amount': roi.deposit_amount,
                })
        return data
    
    def get_dailySummary(self, obj):
        """
        Returns a simplified summary of user's financial activity:
        - balanceUntilYesterday: Total balance including ROIs up to yesterday
        - todaysTransactions: List of today's transactions (serialized)
        """
        today = timezone.now()
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Balance until yesterday
        balance_until_yesterday = calculate_rois_by_date(obj, today)
        
        # Today's approved transactions
        todays_transactions = Transaction.objects.filter(
            created_at__gte=start_of_day
        ).filter(
            is_approved=True
        ).filter(
            is_deposit=False
        ).filter(
            # Transactions where the user is either the origin or destination
            models.Q(origin__owner=obj) | models.Q(destination__owner=obj)
        ).order_by('-created_at')
        
        # Serialize the transactions
        transaction_serializer = TransactionListSerializer(
            todays_transactions, 
            many=True,
            context={'request': self.context.get('request')}
        )
        
        return {
            'balanceUntilYesterday': balance_until_yesterday,
            'todaysTransactions': transaction_serializer.data
        }