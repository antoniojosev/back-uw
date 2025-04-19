import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.wallet.models import Wallet
from django.db import transaction

User = get_user_model()

SYSTEM_WALLET_UUID = "11111111-1111-1111-1111-111111111111"


class Command(BaseCommand):
    help = 'Creates a system wallet with a predetermined UUID for handling deposits and withdrawals'

    def handle(self, *args, **options):
        # Check if system wallet already exists
        try:
            wallet = Wallet.objects.get(id=SYSTEM_WALLET_UUID)
            self.stdout.write(
                self.style.WARNING(f'System wallet already exists with ID {wallet.id}')
            )
            return
        except Wallet.DoesNotExist:
            # Try to find or create system user
            system_user, created = User.objects.get_or_create(
                username='system_wallet',
                defaults={
                    'email': 'system@example.com',
                    'is_staff': True,
                    'is_active': True
                }
            )
            
            if created:
                system_user.set_password(str(uuid.uuid4()))
                system_user.save()
                self.stdout.write(
                    self.style.SUCCESS('Created system user: system_wallet')
                )
                
            # Create system wallet with predetermined UUID
            with transaction.atomic():
                wallet = Wallet(
                    id=SYSTEM_WALLET_UUID,
                    owner=system_user,
                    address='SYSTEM_WALLET',
                    balance=0,
                    is_active=True
                )
                wallet.save()
                
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created system wallet with ID {wallet.id}')
            )