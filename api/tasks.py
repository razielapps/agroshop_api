# tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from .models import Trade, PaymentTransaction, Item, UserProfile

logger = logging.getLogger(__name__)


@shared_task
def process_withdrawal(transaction_id):
    """
    Process withdrawal transaction asynchronously
    """
    try:
        transaction = PaymentTransaction.objects.get(id=transaction_id)
        
        # Simulate bank processing delay
        import time
        time.sleep(2)  # Remove in production
        
        # Mark as completed
        transaction.status = 'completed'
        transaction.completed_at = timezone.now()
        transaction.save()
        
        # Send notification
        send_mail(
            subject='Withdrawal Processed',
            message=f'Your withdrawal of ₦{transaction.amount} has been processed.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[transaction.user.email],
            fail_silently=False,
        )
        
        logger.info(f"Withdrawal processed: {transaction.reference}")
        
    except PaymentTransaction.DoesNotExist:
        logger.error(f"Withdrawal transaction not found: {transaction_id}")
    except Exception as e:
        logger.error(f"Failed to process withdrawal {transaction_id}: {str(e)}")


@shared_task
def notify_trade_update(trade_id, update_type):
    """
    Send notification for trade updates
    """
    try:
        trade = Trade.objects.get(id=trade_id)
        
        if update_type == 'completed':
            subject = 'Trade Completed'
            buyer_message = f"Trade {trade.trade_id} has been marked as complete."
            seller_message = f"Trade {trade.trade_id} has been completed. Funds have been released to your account."
            
            # Send to buyer
            send_mail(
                subject=subject,
                message=buyer_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[trade.buyer.email],
                fail_silently=False,
            )
            
            # Send to seller
            send_mail(
                subject=subject,
                message=seller_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[trade.seller.email],
                fail_silently=False,
            )
            
        elif update_type == 'disputed':
            subject = 'Trade Disputed'
            message = f"Trade {trade.trade_id} has been disputed. Please check the dispute center."
            
            # Send to both parties
            for user in [trade.buyer, trade.seller]:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
        
        logger.info(f"Trade update notified: {trade.trade_id} - {update_type}")
        
    except Trade.DoesNotExist:
        logger.error(f"Trade not found: {trade_id}")


@shared_task
def expire_old_items():
    """
    Expire items that are past their expiry date
    """
    try:
        expired_items = Item.objects.filter(
            status='active',
            expires_at__lt=timezone.now()
        )
        
        count = expired_items.update(status='expired')
        
        logger.info(f"Expired {count} items")
        
    except Exception as e:
        logger.error(f"Failed to expire items: {str(e)}")


@shared_task
def update_user_ratings():
    """
    Update user ratings based on completed trades
    """
    try:
        # Get all users with completed trades
        profiles = UserProfile.objects.filter(
            user__seller_trades__status='completed'
        ).distinct()
        
        for profile in profiles:
            # Calculate average rating
            trades = profile.user.seller_trades.filter(
                status='completed',
                seller_rating__isnull=False
            )
            
            if trades.exists():
                total_rating = sum(trade.seller_rating for trade in trades)
                count = trades.count()
                
                profile.rating = total_rating / count
                profile.total_rating_count = count
                profile.completed_trades = count
                profile.save()
        
        logger.info(f"Updated ratings for {profiles.count()} users")
        
    except Exception as e:
        logger.error(f"Failed to update ratings: {str(e)}")


@shared_task
def cleanup_old_data():
    """
    Clean up old data to keep database optimized
    """
    try:
        # Delete old completed trades (older than 1 year)
        cutoff_date = timezone.now() - timedelta(days=365)
        old_trades = Trade.objects.filter(
            status='completed',
            completed_at__lt=cutoff_date
        )
        trade_count = old_trades.count()
        old_trades.delete()
        
        # Delete old messages (older than 6 months)
        message_cutoff = timezone.now() - timedelta(days=180)
        old_messages = TradeMessage.objects.filter(
            created_at__lt=message_cutoff
        )
        message_count = old_messages.count()
        old_messages.delete()
        
        logger.info(f"Cleaned up {trade_count} old trades and {message_count} old messages")
        
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {str(e)}")