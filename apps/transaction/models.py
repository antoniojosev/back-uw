from django.db import models
from django.contrib.auth import get_user_model
from utils.models import BaseModel
from apps.wallet.models import Wallet

User = get_user_model()


class Transaction(BaseModel):
    """
    Model representing a transaction between wallets.
    """
    origin = models.ForeignKey(
        Wallet,
        on_delete=models.SET_NULL,
        null=True,
        related_name='outgoing_transactions'
    )
    destination = models.ForeignKey(
        Wallet,
        on_delete=models.SET_NULL,
        null=True,
        related_name='incoming_transactions'
    )
    amount = models.DecimalField(
        max_digits=40,
        decimal_places=8
    )
    is_pending = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    is_deposit = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_transactions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    hash = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )

    def __str__(self):
        origin_str = self.origin.address if self.origin else "External"
        destination_str = self.destination.address if self.destination else "External"
        return f"Transaction: {origin_str} → {destination_str} ({self.amount})"
