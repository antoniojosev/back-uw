from django.db import models
from django.contrib.auth import get_user_model
from utils.models import BaseModel

User = get_user_model()


class Wallet(BaseModel):
    """
    Model representing a user's digital wallet.
    """
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wallets'
    )
    balance = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=0
    )
    address = models.CharField(
        max_length=255,
        unique=True, 
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    last_transaction_date = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Wallet {self.address} - {self.owner.email}"
