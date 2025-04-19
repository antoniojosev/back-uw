from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    User profile serializer with specific fields requested.
    """
    walletAddress = serializers.CharField(read_only=True, required=False)  # Not in model
    balance = serializers.SerializerMethodField(read_only=True, required=False)  # Not in model
    isAdmin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'walletAddress', 'balance', 'isAdmin']
        read_only_fields = ['id', 'email', 'name', 'isAdmin']

    def get_balance(self, obj):
        """
        Return the user's balance.
        """
        return obj.wallets.first().balance

    def get_isAdmin(self, obj):
        """
        Return whether the user is an admin.
        """
        return obj.is_staff