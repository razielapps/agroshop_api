# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q, Sum, F, Case, When, Value
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
import logging

from .models import (
    User, UserProfile, Category, Subcategory, Item, Trade, 
    TradeMessage, UserBalance, PaymentTransaction, Dispute, 
    UserVerification, ItemImage, ItemOption, ItemVariant
)
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserBalanceSerializer, CategorySerializer, SubcategorySerializer,
    ItemSerializer, ItemCreateSerializer, TradeSerializer, 
    TradeCreateSerializer, TradeMessageSerializer, PaymentTransactionSerializer,
    DisputeSerializer, UserVerificationSerializer, RechargeBalanceSerializer,
    ItemVariantSerializer, ItemOptionSerializer
)
from .permissions import (
    IsVerifiedUser, IsTradeParticipant, IsItemOwner, 
    CanPostItems, CanOpenTrade, IsOwnerOrReadOnly
)
from .utils import send_email_notification, validate_trade_amount
from .tasks import process_withdrawal, notify_trade_update

logger = logging.getLogger(__name__)


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Create user profile
            UserProfile.objects.create(user=user)
            
            # Create user balance record
            UserBalance.objects.create(user=user)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserProfileSerializer(user.profile).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Update last login
            user.last_login = timezone.now()
            user.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserProfileSerializer(user.profile).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def patch(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        balance = request.user.balance
        serializer = UserBalanceSerializer(balance)
        return Response(serializer.data)


class RechargeBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RechargeBalanceSerializer(data=request.data)
        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            payment_method = serializer.validated_data.get('payment_method', 'gateway')
            
            # Create pending transaction
            transaction = PaymentTransaction.objects.create(
                user=request.user,
                amount=amount,
                transaction_type='deposit',
                status='pending',
                payment_method=payment_method,
                reference=f"RECHARGE_{request.user.id}_{timezone.now().timestamp()}"
            )
            
            # Mock payment gateway integration point
            # In production, this would redirect to payment gateway
            # For now, simulate successful payment
            transaction.status = 'completed'
            transaction.save()
            
            # Update user balance
            balance = request.user.balance
            balance.normal_balance += amount
            balance.save()
            
            return Response({
                'message': 'Recharge successful',
                'transaction': PaymentTransactionSerializer(transaction).data,
                'new_balance': balance.normal_balance
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WithdrawalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        amount = request.data.get('amount')
        bank_details = request.data.get('bank_details', {})
        
        if not amount or float(amount) <= 0:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        balance = request.user.balance
        
        if balance.normal_balance < float(amount):
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user has any pending withdrawals
        pending_withdrawals = PaymentTransaction.objects.filter(
            user=request.user,
            transaction_type='withdrawal',
            status='pending'
        ).exists()
        
        if pending_withdrawals:
            return Response({'error': 'You have a pending withdrawal'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create withdrawal transaction
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            amount=amount,
            transaction_type='withdrawal',
            status='pending',
            payment_method='bank_transfer',
            details=bank_details,
            reference=f"WITHDRAW_{request.user.id}_{timezone.now().timestamp()}"
        )
        
        # Deduct from balance immediately
        balance.normal_balance -= float(amount)
        balance.save()
        
        # Process withdrawal asynchronously
        process_withdrawal.delay(transaction.id)
        
        return Response({
            'message': 'Withdrawal request submitted',
            'transaction': PaymentTransactionSerializer(transaction).data
        })


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Category.objects.filter(is_active=True).prefetch_related('subcategories')
    serializer_class = CategorySerializer
    pagination_class = None


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Item.objects.filter(
            Q(status='active') | Q(user=self.request.user if self.request.user.is_authenticated else None)
        ).select_related('user', 'category', 'subcategory').prefetch_related('images', 'variants', 'options')
        
        # Filters
        category = self.request.query_params.get('category')
        subcategory = self.request.query_params.get('subcategory')
        trade_type = self.request.query_params.get('trade_type')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        search = self.request.query_params.get('search')
        
        if category:
            queryset = queryset.filter(category_id=category)
        if subcategory:
            queryset = queryset.filter(subcategory_id=subcategory)
        if trade_type:
            queryset = queryset.filter(trade_type=trade_type)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(category__name__icontains=search) |
                Q(subcategory__name__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ItemCreateSerializer
        return ItemSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            self.permission_classes = [permissions.IsAuthenticated, CanPostItems]
        elif self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated, IsItemOwner]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
        # Track user's ad count for unverified users
        if not self.request.user.profile.is_verified:
            profile = self.request.user.profile
            profile.active_ads_count = Item.objects.filter(
                user=self.request.user,
                status='active'
            ).count()
            profile.save()
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def toggle_favorite(self, request, pk=None):
        item = self.get_object()
        profile = request.user.profile
        
        if item in profile.favorites.all():
            profile.favorites.remove(item)
            return Response({'status': 'removed from favorites'})
        else:
            profile.favorites.add(item)
            return Response({'status': 'added to favorites'})


class TradeViewSet(viewsets.ModelViewSet):
    serializer_class = TradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see trades they're involved in
        return Trade.objects.filter(
            Q(buyer=self.request.user) | Q(seller=self.request.user)
        ).select_related('buyer', 'seller', 'item').prefetch_related(
            'messages', 'disputes'
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action in ['create']:
            return TradeCreateSerializer
        return TradeSerializer
    
    @action(detail=False, methods=['get'])
    def my_trades(self, request):
        trades = self.get_queryset()
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            trades = trades.filter(status=status_filter)
        
        page = self.paginate_queryset(trades)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(trades, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        serializer = TradeCreateSerializer(data=request.data)
        if serializer.is_valid():
            item_id = serializer.validated_data['item_id']
            quantity = serializer.validated_data.get('quantity', 1)
            selected_variants = serializer.validated_data.get('selected_variants', [])
            selected_options = serializer.validated_data.get('selected_options', [])
            
            try:
                item = Item.objects.get(id=item_id, status='active')
            except Item.DoesNotExist:
                return Response({'error': 'Item not available'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user can open trade
            if not CanOpenTrade().has_object_permission(request, self, item):
                return Response(
                    {'error': 'Trade limit exceeded or verification required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate trade amount based on user verification
            max_amount = validate_trade_amount(request.user, item.price * quantity)
            if item.price * quantity > max_amount:
                return Response(
                    {'error': f'Maximum trade amount for unverified users is ${max_amount}'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check buyer balance
            buyer_balance = request.user.balance
            total_price = item.price * quantity
            
            if buyer_balance.normal_balance < total_price:
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Deduct from buyer's balance
            buyer_balance.normal_balance -= total_price
            buyer_balance.save()
            
            # Create trade
            trade = Trade.objects.create(
                buyer=request.user,
                seller=item.user,
                item=item,
                quantity=quantity,
                total_amount=total_price,
                selected_variants=selected_variants,
                selected_options=selected_options,
                status='active'
            )
            
            # Credit seller's pending balance
            seller_balance = item.user.balance
            seller_balance.pending_balance += total_price
            seller_balance.save()
            
            # Create initial chat message
            TradeMessage.objects.create(
                trade=trade,
                sender=request.user,
                message=f"Trade initiated for {item.title}"
            )
            
            # Notify seller
            send_email_notification(
                item.user.email,
                'New Trade Initiated',
                f'A buyer has initiated a trade for your item: {item.title}'
            )
            
            return Response(TradeSerializer(trade).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsTradeParticipant])
    def mark_complete(self, request, pk=None):
        trade = self.get_object()
        
        if trade.status != 'active':
            return Response({'error': 'Trade is not active'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Only buyer can mark as complete
        if trade.buyer != request.user:
            return Response({'error': 'Only buyer can mark trade as complete'}, status=status.HTTP_403_FORBIDDEN)
        
        # Update trade status
        trade.status = 'completed'
        trade.completed_at = timezone.now()
        trade.save()
        
        # Move funds from seller's pending to normal balance
        seller_balance = trade.seller.balance
        seller_balance.pending_balance -= trade.total_amount
        seller_balance.normal_balance += trade.total_amount
        seller_balance.save()
        
        # Update item quantity if applicable
        if trade.item.quantity is not None:
            trade.item.quantity -= trade.quantity
            if trade.item.quantity <= 0:
                trade.item.status = 'sold'
            trade.item.save()
        
        # Notify seller
        notify_trade_update.delay(trade.id, 'completed')
        
        return Response({'status': 'Trade marked as complete'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsTradeParticipant])
    def open_dispute(self, request, pk=None):
        trade = self.get_object()
        
        if trade.status != 'active':
            return Response({'error': 'Trade is not active'}, status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('reason', '')
        description = request.data.get('description', '')
        
        if not reason:
            return Response({'error': 'Reason is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create dispute
        dispute = Dispute.objects.create(
            trade=trade,
            opened_by=request.user,
            reason=reason,
            description=description,
            status='open'
        )
        
        # Update trade status
        trade.status = 'disputed'
        trade.save()
        
        # Notify admin and other party
        notify_trade_update.delay(trade.id, 'disputed')
        
        return Response(DisputeSerializer(dispute).data)
    
    @action(detail=True, methods=['get'], permission_classes=[IsTradeParticipant])
    def messages(self, request, pk=None):
        trade = self.get_object()
        messages = trade.messages.all().order_by('created_at')
        serializer = TradeMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsTradeParticipant])
    def send_message(self, request, pk=None):
        trade = self.get_object()
        
        if trade.status not in ['active', 'disputed']:
            return Response({'error': 'Cannot send messages in this trade status'}, status=status.HTTP_400_BAD_REQUEST)
        
        message_text = request.data.get('message', '')
        
        if not message_text:
            return Response({'error': 'Message cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        message = TradeMessage.objects.create(
            trade=trade,
            sender=request.user,
            message=message_text
        )
        
        return Response(TradeMessageSerializer(message).data)


class DisputeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see disputes they're involved in
        return Dispute.objects.filter(
            Q(trade__buyer=self.request.user) | 
            Q(trade__seller=self.request.user)
        ).select_related('trade', 'opened_by', 'resolved_by').order_by('-created_at')
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def resolve(self, request, pk=None):
        dispute = self.get_object()
        
        if dispute.status != 'open':
            return Response({'error': 'Dispute is already resolved'}, status=status.HTTP_400_BAD_REQUEST)
        
        resolution = request.data.get('resolution', 'refund_buyer')
        notes = request.data.get('notes', '')
        
        dispute.status = 'resolved'
        dispute.resolution = resolution
        dispute.resolution_notes = notes
        dispute.resolved_by = request.user
        dispute.resolved_at = timezone.now()
        dispute.save()
        
        # Handle resolution
        trade = dispute.trade
        
        if resolution == 'refund_buyer':
            # Refund buyer
            buyer_balance = trade.buyer.balance
            buyer_balance.normal_balance += trade.total_amount
            buyer_balance.save()
            
            # Deduct from seller's pending balance
            seller_balance = trade.seller.balance
            seller_balance.pending_balance -= trade.total_amount
            seller_balance.save()
            
            trade.status = 'cancelled'
        
        elif resolution == 'release_to_seller':
            # Release funds to seller
            seller_balance = trade.seller.balance
            seller_balance.pending_balance -= trade.total_amount
            seller_balance.normal_balance += trade.total_amount
            seller_balance.save()
            
            trade.status = 'completed'
        
        elif resolution == 'partial_refund':
            # Split amount
            refund_percentage = float(request.data.get('refund_percentage', 50)) / 100
            refund_amount = trade.total_amount * refund_percentage
            seller_amount = trade.total_amount - refund_amount
            
            # Refund buyer partially
            buyer_balance = trade.buyer.balance
            buyer_balance.normal_balance += refund_amount
            buyer_balance.save()
            
            # Release partial to seller
            seller_balance = trade.seller.balance
            seller_balance.pending_balance -= trade.total_amount
            seller_balance.normal_balance += seller_amount
            seller_balance.save()
            
            trade.status = 'completed'
        
        trade.save()
        
        # Notify both parties
        notify_trade_update.delay(trade.id, f'dispute_resolved_{resolution}')
        
        return Response(DisputeSerializer(dispute).data)


class UserVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Check if already verified
        if request.user.profile.is_verified:
            return Response({'error': 'User is already verified'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = UserVerificationSerializer(data=request.data)
        if serializer.is_valid():
            verification = serializer.save(user=request.user)
            
            # In production, this would trigger verification process
            # For now, auto-verify for demo
            verification.status = 'pending'
            verification.save()
            
            return Response({
                'message': 'Verification submitted',
                'verification': UserVerificationSerializer(verification).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = user.profile
        
        # Get user stats
        active_trades = Trade.objects.filter(
            Q(buyer=user) | Q(seller=user),
            status='active'
        ).count()
        
        completed_trades = Trade.objects.filter(
            Q(buyer=user) | Q(seller=user),
            status='completed'
        ).count()
        
        total_sales = Trade.objects.filter(
            seller=user,
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        total_purchases = Trade.objects.filter(
            buyer=user,
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Recent trades
        recent_trades = Trade.objects.filter(
            Q(buyer=user) | Q(seller=user)
        ).order_by('-created_at')[:5]
        
        # Recent transactions
        recent_transactions = PaymentTransaction.objects.filter(
            user=user
        ).order_by('-created_at')[:10]
        
        return Response({
            'profile': UserProfileSerializer(profile).data,
            'balance': UserBalanceSerializer(user.balance).data,
            'stats': {
                'active_trades': active_trades,
                'completed_trades': completed_trades,
                'total_sales': total_sales,
                'total_purchases': total_purchases,
                'active_ads': Item.objects.filter(user=user, status='active').count(),
                'total_ads': Item.objects.filter(user=user).count(),
            },
            'recent_trades': TradeSerializer(recent_trades, many=True).data,
            'recent_transactions': PaymentTransactionSerializer(recent_transactions, many=True).data,
        })


class UserAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        
        # Check if user has any active trades
        active_trades = Trade.objects.filter(
            Q(buyer=user) | Q(seller=user),
            status='active'
        ).exists()
        
        if active_trades:
            return Response(
                {'error': 'Cannot delete account with active trades'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check last trade age
        last_trade = Trade.objects.filter(
            Q(buyer=user) | Q(seller=user)
        ).order_by('-created_at').first()
        
        if last_trade and last_trade.created_at > timezone.now() - timedelta(days=7):
            return Response(
                {'error': 'Cannot delete account within 7 days of last trade'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has pending balance
        if user.balance.pending_balance > 0 or user.balance.normal_balance > 0:
            return Response(
                {'error': 'Please withdraw all funds before deleting account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mark user as inactive (soft delete)
        user.is_active = False
        user.email = f"deleted_{user.id}_{user.email}"
        user.username = f"deleted_{user.id}_{user.username}"
        user.save()
        
        # Deactivate all active items
        Item.objects.filter(user=user, status='active').update(status='inactive')
        
        return Response({'message': 'Account deleted successfully'})


# Admin Views
class AdminDashboardView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        # System statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        verified_users = User.objects.filter(profile__is_verified=True).count()
        
        total_trades = Trade.objects.count()
        active_trades = Trade.objects.filter(status='active').count()
        disputed_trades = Trade.objects.filter(status='disputed').count()
        
        total_items = Item.objects.count()
        active_items = Item.objects.filter(status='active').count()
        
        total_volume = Trade.objects.filter(status='completed').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Pending verifications
        pending_verifications = UserVerification.objects.filter(status='pending').count()
        
        # Open disputes
        open_disputes = Dispute.objects.filter(status='open').count()
        
        return Response({
            'stats': {
                'users': {
                    'total': total_users,
                    'active': active_users,
                    'verified': verified_users,
                },
                'trades': {
                    'total': total_trades,
                    'active': active_trades,
                    'disputed': disputed_trades,
                    'total_volume': total_volume,
                },
                'items': {
                    'total': total_items,
                    'active': active_items,
                },
                'pending': {
                    'verifications': pending_verifications,
                    'disputes': open_disputes,
                }
            }
        })


class AdminUserManagementView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        user_id = request.data.get('user_id')
        action = request.data.get('action')
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if action == 'verify':
            user.profile.is_verified = True
            user.profile.save()
            
            # Update any pending verification
            UserVerification.objects.filter(user=user, status='pending').update(
                status='approved',
                reviewed_by=request.user,
                reviewed_at=timezone.now()
            )
            
            return Response({'message': 'User verified successfully'})
        
        elif action == 'suspend':
            user.is_active = False
            user.save()
            return Response({'message': 'User suspended successfully'})
        
        elif action == 'activate':
            user.is_active = True
            user.save()
            return Response({'message': 'User activated successfully'})
        
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)