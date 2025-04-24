from django.db import models
from utils.models import BaseModel
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from decimal import Decimal
from apps.transaction.models import Transaction

User = get_user_model()


# Create your models here.

class ROI(BaseModel):
    LEVEL_CHOICES = [
        (1, 'Level 1: $100 - 30% ROI'),
        (2, 'Level 2: $500 - 35% ROI'),
        (3, 'Level 3: $1,000 - 40% ROI'),
        (4, 'Level 4: $3,000 - 50% ROI'),
        (5, 'Level 5: $5,000+ - 60% ROI'),
    ]
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='roi_owners',
        verbose_name='Owner'
    )
    deposit_amount = models.DecimalField(
        max_digits=40,
        decimal_places=8
    )
    level = models.IntegerField(choices=LEVEL_CHOICES)
    roi_percentage = models.DecimalField(
        max_digits=40,
        decimal_places=8
    )
    daily_percentage = models.DecimalField(
        max_digits=40,
        decimal_places=8
    )
    duration_seconds = models.IntegerField()
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='roi_transactions',
        verbose_name='Transaction',
        null=True,
        blank=True
    )

    LEVEL_CONFIG = {
        1: {
            "roi_percentage": 30,
            "daily_percentage": 1.30,
            "duration_days": 100,
        },
        2: {
            "roi_percentage": 35,
            "daily_percentage": 7.50,
            "duration_days": 90,
        },
        3: {
            "roi_percentage": 40,
            "daily_percentage": 17.50,
            "duration_days": 80,
        },
        4: {
            "roi_percentage": 50,
            "daily_percentage": 64.28,
            "duration_days": 70,
        },
        5: {
            "roi_percentage": 60,
            "daily_percentage": 133.33,
            "duration_days": 60,
        },
    }

    @classmethod
    def get_level_by_deposit(cls, deposit):
        if deposit == Decimal('0.3'):
            deposit = 650
        elif deposit == Decimal('0.1'):
            deposit = 150
        if deposit >= 5000:
            return 5
        elif deposit >= 3000:
            return 4
        elif deposit >= 1000:
            return 3
        elif deposit >= 500:
            return 2
        elif deposit >= 100:
            return 1
        else:
            raise ValueError("Deposit is too low to assign a valid ROI.")

    def assign_values_by_level(self):
        level_config = self.LEVEL_CONFIG.get(self.level)
        if level_config:
            self.roi_percentage = level_config["roi_percentage"]
            self.daily_percentage = level_config["daily_percentage"]
            self.duration_seconds = level_config["duration_days"] * 24 * 60 * 60
            if self.deposit_amount == Decimal('0.3'):
                self.deposit_amount = 650
            elif self.deposit_amount == Decimal('0.1'):
                self.deposit_amount = 150
        else:
            raise ValueError("Level configuration not found.")

    def save(self, *args, **kwargs):
        self.level = self.get_level_by_deposit(self.deposit_amount)
        self.assign_values_by_level()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Level {self.level}: {self.deposit_amount} - {self.roi_percentage}% ROI"

    @property
    def time_remaining(self):
        """Calculate the time remaining for this ROI based on creation date and duration.
        Returns a timedelta object representing how much time remains until the ROI period ends.
        If the ROI period has ended, returns timedelta(0).
        All time calculations use UTC timezone.
        """
        # Calculate end date by adding duration to created_at
        end_date = self.created_at + timedelta(seconds=self.duration_seconds)
        
        # Calculate the remaining time between now and the end date
        now = timezone.now()
        remaining = end_date - now
        
        # If remaining time is negative, return zero
        if remaining.total_seconds() < 0:
            return timedelta(0)
            
        return remaining
            
    @property
    def current_earnings(self):
        """Calculate how much has been earned so far based on creation date, elapsed time, and daily percentage.
        Returns a decimal value representing the current earnings in the same currency as the deposit.
        The earnings accumulate continuously (per second) based on the daily percentage rate.
        """
        from decimal import Decimal
        
        now = timezone.now()
        elapsed_time = now - self.created_at
        total_seconds_elapsed = elapsed_time.total_seconds()
        
        # Calculate daily earnings
        daily_earnings = self.deposit_amount * self.daily_percentage / 100
        
        # Calculate earnings per second
        seconds_in_day = 24 * 60 * 60  # 86400 seconds
        earnings_per_second = daily_earnings / Decimal(str(seconds_in_day))
        
        # Calculate current earnings based on elapsed seconds
        current_earnings = earnings_per_second * Decimal(str(total_seconds_elapsed))
        
        # If the total duration has passed, cap at the total expected ROI
        total_duration = timedelta(seconds=self.duration_seconds)
        if elapsed_time >= total_duration:
            return self.deposit_amount * self.roi_percentage / 100
            
        return round(current_earnings, 10)

