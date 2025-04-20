from apps.transaction.models import Transaction
from apps.roi.models import ROI
from datetime import datetime, time, timedelta
from django.utils import timezone
from decimal import Decimal

def calculate_balance(user):
    """
    Calculate the total balance from a list of wallets.
    """
    total_balance = 0
    for transaction in Transaction.objects.filter(origin=user.wallets.first(), is_deposit=True):
        total_balance += transaction.amount
    for transaction in Transaction.objects.filter(destination=user.wallets.first(), is_deposit=False, is_approved=True):
        total_balance -= transaction.amount
    return total_balance

def calculate_rois(user):
    """
    Calculate the total ROI for a user.
    """
    total_roi = 0
    rois = ROI.objects.filter(owner=user)
    for roi in rois:
        if(roi.time_remaining.total_seconds() > 0):
            earnings = roi.current_earnings
            total_roi += earnings
    
    withdrawals = Transaction.objects.filter(destination=user.wallets.first(), is_deposit=False, is_approved=True)
    for withdrawal in withdrawals:
        total_roi -= withdrawal.amount
    return total_roi

def calculate_balance_total(user):
    """
    Calculate the total balance including ROIs for a user.
    """
    balance = calculate_balance(user)
    rois = calculate_rois(user)
    return balance + rois

def calculate_balance_by_date(user, target_date):
    """
    Calculate the total balance from a list of wallets up to the specified date.
    The function excludes transactions from the day of the target_date.
    
    Args:
        user: The user object
        target_date: datetime object specifying the cutoff date
    
    Returns:
        Decimal: Total balance up to the day before the target_date
    """
    # Convert target_date to the start of the day
    if isinstance(target_date, datetime):
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # If a date object is passed
        start_of_day = datetime.combine(target_date, time.min)
    
    total_balance = 0
    
    # Get deposits up to the start of the target day
    deposits = Transaction.objects.filter(
        origin=user.wallets.first(),
        is_deposit=True,
        created_at__lt=start_of_day
    )
    
    for transaction in deposits:
        total_balance += transaction.amount
    
    # Get withdrawals up to the start of the target day
    withdrawals = Transaction.objects.filter(
        destination=user.wallets.first(), 
        is_deposit=False, 
        is_approved=True,
        created_at__lt=start_of_day
    )
    
    for transaction in withdrawals:
        total_balance -= transaction.amount
        
    return total_balance

def calculate_rois_by_date(user, target_date):
    """
    Calculate the total ROI for a user up to the specified date.
    The function calculates earnings up to the day before the target_date.
    
    Args:
        user: The user object
        target_date: datetime object specifying the cutoff date
    
    Returns:
        Decimal: Total ROI earnings up to the day before the target_date
    """
    # Convert target_date to the start of the day
    if isinstance(target_date, datetime):
        cutoff_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # If a date object is passed
        cutoff_date = datetime.combine(target_date, time.min)
    
    total_roi = Decimal('0')
    rois = ROI.objects.filter(owner=user, created_at__lt=cutoff_date)
    
    for roi in rois:
        # Skip if ROI has no time remaining at the cutoff date
        end_date = roi.created_at + timedelta(seconds=roi.duration_seconds)
        if end_date <= cutoff_date:
            # For completed ROIs, add the full earnings
            total_roi += roi.deposit_amount * roi.roi_percentage / Decimal('100')
            continue
            
        # Calculate elapsed time between ROI creation and the cutoff date
        elapsed_time = cutoff_date - roi.created_at
        elapsed_seconds = elapsed_time.total_seconds()
        
        if elapsed_seconds <= 0:
            continue
            
        # Calculate daily earnings
        daily_earnings = roi.deposit_amount * roi.daily_percentage / Decimal('100')
        
        # Calculate earnings per second
        seconds_in_day = 24 * 60 * 60  # 86400 seconds
        earnings_per_second = daily_earnings / Decimal(str(seconds_in_day))
        
        # Calculate current earnings based on elapsed seconds
        current_earnings = earnings_per_second * Decimal(str(elapsed_seconds))
        
        total_roi += round(current_earnings, 10)
    
    # Subtract any withdrawals made before the cutoff date
    withdrawals = Transaction.objects.filter(
        destination=user.wallets.first(), 
        is_deposit=False, 
        is_approved=True,
        created_at__lt=cutoff_date
    )
    for withdrawal in withdrawals:
        total_roi -= withdrawal.amount
    # Ensure total ROI is not negative
    if total_roi < 0:
        total_roi = Decimal('0')
    
    return total_roi

def calculate_balance_total_by_date(user, target_date=None):
    """
    Calculate the total balance including ROIs for a user up to the specified date.
    If no date is provided, it uses the current date (which will exclude today's transactions).
    
    Args:
        user: The user object
        target_date: datetime object specifying the cutoff date (default: current date)
    
    Returns:
        Decimal: Total balance including ROIs up to the day before the target_date
    """
    if target_date is None:
        target_date = timezone.now()
        
    balance = calculate_balance_by_date(user, target_date)
    rois = calculate_rois_by_date(user, target_date)
    
    return balance + rois