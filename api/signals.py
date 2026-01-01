# signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import User, UserProfile, UserBalance, Trade, Item


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_user_balance(sender, instance, created, **kwargs):
    if created:
        UserBalance.objects.create(user=instance)


@receiver(post_save, sender=Trade)
def update_user_stats_on_trade_completion(sender, instance, created, **kwargs):
    if not created and instance.status == 'completed':
        # Update seller's completed trades count
        seller_profile = instance.seller.profile
        seller_profile.completed_trades += 1
        seller_profile.save()
        
        # Update buyer's stats if needed
        buyer_profile = instance.buyer.profile
        buyer_profile.save()


@receiver(pre_save, sender=Item)
def update_ad_count_on_item_status_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_item = Item.objects.get(pk=instance.pk)
            if old_item.status != instance.status:
                profile = instance.user.profile
                
                if instance.status == 'active':
                    profile.active_ads_count = Item.objects.filter(
                        user=instance.user,
                        status='active'
                    ).count()
                elif old_item.status == 'active' and instance.status != 'active':
                    profile.active_ads_count = max(0, profile.active_ads_count - 1)
                
                profile.save()
        except Item.DoesNotExist:
            pass