# permissions.py
from rest_framework import permissions
from django.utils import timezone
from datetime import timedelta

from .models import Item, Trade


class IsVerifiedUser(permissions.BasePermission):
    """Check if user is verified"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.is_verified


class IsTradeParticipant(permissions.BasePermission):
    """Check if user is a participant in the trade"""
    
    def has_object_permission(self, request, view, obj):
        return request.user in [obj.buyer, obj.seller]


class IsItemOwner(permissions.BasePermission):
    """Check if user is the owner of the item"""
    
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class CanPostItems(permissions.BasePermission):
    """Check if user can post items based on verification status"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        profile = request.user.profile
        
        # Verified users can post unlimited
        if profile.is_verified:
            return True
        
        # Unverified users: max 5 active ads
        max_ads = 5
        active_ads = Item.objects.filter(user=request.user, status='active').count()
        
        if active_ads >= max_ads:
            return False
        
        # Unverified users: max 3 ads per day
        time_limit = timezone.now() - timedelta(hours=24)
        recent_ads = Item.objects.filter(
            user=request.user,
            created_at__gte=time_limit
        ).count()
        
        return recent_ads < 3


class CanOpenTrade(permissions.BasePermission):
    """Check if user can open a new trade"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        profile = request.user.profile
        
        # Verified users can open unlimited trades
        if profile.is_verified:
            return True
        
        # Unverified users: check active trades limit
        max_active_trades = 3
        active_trades = Trade.objects.filter(
            buyer=request.user,
            status='active'
        ).count()
        
        return active_trades < max_active_trades
    
    def has_object_permission(self, request, view, obj):
        # For item objects, check if user can open trade for this item
        return self.has_permission(request, view)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level permission to only allow owners to edit"""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return obj.user == request.user