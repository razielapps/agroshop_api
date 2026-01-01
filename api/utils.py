# utils.py
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def send_email_notification(to_email, subject, message):
    """
    Send email notification to user
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info(f"Email sent to {to_email}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")


def validate_trade_amount(user, amount):
    """
    Validate trade amount based on user verification status
    """
    if user.profile.is_verified:
        # Verified users have no limit
        return float('inf')
    
    # Unverified users have limits
    max_amount = 500000  # ₦500,000 max for unverified users
    
    # Check daily trade volume for unverified users
    today = timezone.now().date()
    today_trades = user.buyer_trades.filter(
        created_at__date=today,
        status__in=['active', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    daily_limit = 1000000  # ₦1,000,000 daily limit
    
    if today_trades + amount > daily_limit:
        return daily_limit - today_trades
    
    return max_amount


def calculate_ad_expiry(user):
    """
    Calculate ad expiry date based on user verification status
    """
    if user.profile.is_verified:
        # Verified users: 60 days
        return timezone.now() + timedelta(days=60)
    else:
        # Unverified users: 30 days
        return timezone.now() + timedelta(days=30)


def generate_payment_reference(user, transaction_type):
    """
    Generate unique payment reference
    """
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    user_id = str(user.id).zfill(6)
    return f"{transaction_type.upper()}_{user_id}_{timestamp}"


def check_user_can_delete_account(user):
    """
    Check if user can delete their account
    """
    # Check active trades
    if user.buyer_trades.filter(status='active').exists() or \
       user.seller_trades.filter(status='active').exists():
        return False, "Cannot delete account with active trades"
    
    # Check last trade age
    last_trade = user.buyer_trades.order_by('-created_at').first()
    if not last_trade:
        last_trade = user.seller_trades.order_by('-created_at').first()
    
    if last_trade and last_trade.created_at > timezone.now() - timedelta(days=7):
        return False, "Cannot delete account within 7 days of last trade"
    
    # Check pending balance
    if user.balance.pending_balance > 0 or user.balance.normal_balance > 0:
        return False, "Please withdraw all funds before deleting account"
    
    return True, "Account can be deleted"