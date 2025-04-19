from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.wallet.models import Wallet
import uuid

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering new users with password confirmation.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['username', 'email', 'name', 'last_name', 'password', 'password_confirm']
        
    def validate(self, attrs):
        """
        Validate that passwords match and the email is unique.
        """
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': "Las contraseñas no coinciden"})
            
        if User.objects.filter(email=attrs.get('email')).exists():
            raise serializers.ValidationError({'email': "Un usuario con este email ya existe."})
            
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Create the user and wallet in a single transaction.
        """
        # Eliminar el campo password_confirm ya que no es parte del modelo User
        validated_data.pop('password_confirm', None)
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            name=validated_data.get('name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password'],
        )
        
        # Crear wallet automáticamente para el usuario
        Wallet.objects.create(
            owner=user,
            is_active=True
        )
        
        return user