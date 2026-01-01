# serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta
import re

from .models import (
    User, UserProfile, Category, Subcategory, Item, Trade,
    TradeMessage, UserBalance, PaymentTransaction, Dispute,
    UserVerification, ItemImage, ItemVariant, ItemOption
)


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    full_name = serializers.CharField(required=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'full_name', 'password', 'password2')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists."})
        
        return attrs
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            full_name=validated_data['full_name'],
            password=validated_data['password']
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'),
                              email=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Unable to log in with provided credentials.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include "email" and "password".')


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = (
            'email', 'username', 'full_name', 'phone_number', 'address',
            'city', 'state', 'country', 'postal_code', 'profile_picture',
            'bio', 'is_verified', 'verification_date', 'rating',
            'total_rating_count', 'completed_trades', 'active_ads_count',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'is_verified', 'verification_date', 'rating',
            'total_rating_count', 'completed_trades', 'active_ads_count',
            'created_at', 'updated_at'
        )
    
    def validate_phone_number(self, value):
        if value:
            # Basic phone validation
            phone_pattern = r'^\+?[1-9]\d{1,14}$'
            if not re.match(phone_pattern, value.replace(' ', '')):
                raise serializers.ValidationError('Enter a valid phone number.')
        return value


class UserBalanceSerializer(serializers.ModelSerializer):
    total_balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = UserBalance
        fields = ('normal_balance', 'pending_balance', 'total_balance',
                 'total_withdrawn', 'total_deposited', 'created_at', 'updated_at')
        read_only_fields = fields


class RechargeBalanceSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(100)]  # Minimum recharge amount
    )
    payment_method = serializers.ChoiceField(
        choices=PaymentTransaction.PAYMENT_METHODS,
        default='gateway'
    )
    
    def validate_amount(self, value):
        # Maximum recharge amount for unverified users
        user = self.context['request'].user
        if not user.profile.is_verified and value > 500000:  # 500,000 max for unverified
            raise serializers.ValidationError('Maximum recharge amount for unverified users is ₦500,000')
        return value


class CategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'category_type', 'description',
                 'icon', 'is_active', 'sort_order', 'subcategories')
    
    def get_subcategories(self, obj):
        subcategories = obj.subcategories.filter(is_active=True)
        return SubcategorySerializer(subcategories, many=True).data


class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategory
        fields = ('id', 'name', 'slug', 'description', 'is_active')


class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ('id', 'image', 'is_primary', 'caption', 'sort_order', 'created_at')


class ItemVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemVariant
        fields = ('id', 'name', 'value', 'additional_price', 'quantity')


class ItemOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemOption
        fields = ('id', 'name', 'value', 'additional_price')


class ItemSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    
    images = ItemImageSerializer(many=True, read_only=True)
    variants = ItemVariantSerializer(many=True, read_only=True)
    options = ItemOptionSerializer(many=True, read_only=True)
    
    is_favorited = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = (
            'id', 'user', 'user_id', 'category', 'category_name',
            'subcategory', 'subcategory_name', 'title', 'slug',
            'description', 'price', 'price_unit', 'negotiable',
            'trade_type', 'quantity', 'min_order_quantity',
            'location', 'city', 'state', 'country', 'latitude',
            'longitude', 'status', 'is_featured', 'views',
            'rental_period', 'min_rental_days', 'deposit_required',
            'images', 'variants', 'options',
            'is_favorited', 'user_rating',
            'created_at', 'updated_at', 'expires_at'
        )
        read_only_fields = ('slug', 'views', 'created_at', 'updated_at', 'expires_at')
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj in request.user.profile.favorites.all()
        return False
    
    def get_user_rating(self, obj):
        # Calculate average rating from completed trades
        from django.db.models import Avg
        avg_rating = Trade.objects.filter(
            item=obj,
            status='completed',
            seller_rating__isnull=False
        ).aggregate(Avg('seller_rating'))['seller_rating__avg']
        
        return avg_rating or 0


class ItemCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    variants = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    options = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Item
        fields = (
            'category', 'subcategory', 'title', 'description',
            'price', 'price_unit', 'negotiable', 'trade_type',
            'quantity', 'min_order_quantity', 'location', 'city',
            'state', 'country', 'latitude', 'longitude',
            'rental_period', 'min_rental_days', 'deposit_required',
            'images', 'variants', 'options'
        )
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        # Check if unverified user can post more ads
        if not user.profile.is_verified:
            max_ads = 5  # Maximum ads for unverified users
            active_ads = Item.objects.filter(user=user, status='active').count()
            
            if active_ads >= max_ads:
                raise serializers.ValidationError(
                    f'Unverified users can only have {max_ads} active ads. '
                    'Please verify your account to post more ads.'
                )
            
            # Check if user has posted too many ads recently
            time_limit = timezone.now() - timedelta(hours=24)
            recent_ads = Item.objects.filter(
                user=user,
                created_at__gte=time_limit
            ).count()
            
            if recent_ads >= 3:  # Max 3 ads per day for unverified
                raise serializers.ValidationError(
                    'Unverified users can only post 3 ads per day. '
                    'Please verify your account for unlimited posting.'
                )
        
        return attrs
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        variants_data = validated_data.pop('variants', [])
        options_data = validated_data.pop('options', [])
        
        item = Item.objects.create(**validated_data)
        
        # Save images
        for i, image_data in enumerate(images_data):
            ItemImage.objects.create(
                item=item,
                image=image_data,
                is_primary=(i == 0),
                sort_order=i
            )
        
        # Save variants
        for variant_data in variants_data:
            ItemVariant.objects.create(item=item, **variant_data)
        
        # Save options
        for option_data in options_data:
            ItemOption.objects.create(item=item, **option_data)
        
        return item


class TradeMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    
    class Meta:
        model = TradeMessage
        fields = ('id', 'trade', 'sender', 'sender_name', 'sender_email',
                 'message', 'is_read', 'created_at')
        read_only_fields = ('is_read', 'created_at')


class TradeSerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    buyer_email = serializers.CharField(source='buyer.email', read_only=True)
    seller_name = serializers.CharField(source='seller.full_name', read_only=True)
    seller_email = serializers.CharField(source='seller.email', read_only=True)
    item_title = serializers.CharField(source='item.title', read_only=True)
    
    messages = TradeMessageSerializer(many=True, read_only=True)
    disputes = serializers.SerializerMethodField()
    
    class Meta:
        model = Trade
        fields = (
            'id', 'trade_id', 'buyer', 'buyer_name', 'buyer_email',
            'seller', 'seller_name', 'seller_email', 'item', 'item_title',
            'quantity', 'unit_price', 'total_amount', 'selected_variants',
            'selected_options', 'status', 'is_paid', 'buyer_rating',
            'seller_rating', 'buyer_feedback', 'seller_feedback',
            'messages', 'disputes',
            'created_at', 'updated_at', 'completed_at'
        )
        read_only_fields = (
            'trade_id', 'buyer', 'seller', 'unit_price', 'total_amount',
            'status', 'is_paid', 'created_at', 'updated_at', 'completed_at'
        )
    
    def get_disputes(self, obj):
        disputes = obj.disputes.all()
        return DisputeSerializer(disputes, many=True).data if disputes else []


class TradeCreateSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(default=1, min_value=1)
    selected_variants = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )
    selected_options = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )
    
    def validate(self, attrs):
        item_id = attrs.get('item_id')
        quantity = attrs.get('quantity', 1)
        
        try:
            item = Item.objects.get(id=item_id, status='active')
        except Item.DoesNotExist:
            raise serializers.ValidationError({'item_id': 'Item not found or not active'})
        
        # Check quantity
        if item.quantity is not None and quantity > item.quantity:
            raise serializers.ValidationError(
                {'quantity': f'Only {item.quantity} units available'}
            )
        
        # Validate variants
        selected_variants = attrs.get('selected_variants', [])
        if selected_variants:
            variant_ids = ItemVariant.objects.filter(
                item=item,
                id__in=selected_variants
            ).values_list('id', flat=True)
            
            if len(variant_ids) != len(selected_variants):
                raise serializers.ValidationError(
                    {'selected_variants': 'Invalid variant selection'}
                )
        
        # Validate options
        selected_options = attrs.get('selected_options', [])
        if selected_options:
            option_ids = ItemOption.objects.filter(
                item=item,
                id__in=selected_options
            ).values_list('id', flat=True)
            
            if len(option_ids) != len(selected_options):
                raise serializers.ValidationError(
                    {'selected_options': 'Invalid option selection'}
                )
        
        attrs['item'] = item
        return attrs


class DisputeSerializer(serializers.ModelSerializer):
    trade_id = serializers.CharField(source='trade.trade_id', read_only=True)
    opened_by_name = serializers.CharField(source='opened_by.full_name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Dispute
        fields = (
            'id', 'trade', 'trade_id', 'opened_by', 'opened_by_name',
            'reason', 'description', 'evidence', 'status', 'resolution',
            'resolution_notes', 'resolved_by', 'resolved_by_name',
            'resolved_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('resolved_by', 'resolved_at', 'created_at', 'updated_at')


class PaymentTransactionSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    trade_id = serializers.CharField(source='trade.trade_id', read_only=True, allow_null=True)
    
    class Meta:
        model = PaymentTransaction
        fields = (
            'id', 'user', 'user_email', 'transaction_type', 'amount',
            'status', 'payment_method', 'trade', 'trade_id', 'reference',
            'gateway_reference', 'gateway_response', 'bank_name',
            'account_number', 'account_name', 'details', 'created_at',
            'updated_at', 'completed_at'
        )
        read_only_fields = fields


class UserVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserVerification
        fields = (
            'id', 'document_type', 'document_number',
            'front_image', 'back_image', 'selfie_image',
            'status', 'rejection_reason', 'reviewed_by',
            'reviewed_at', 'submitted_at', 'updated_at'
        )
        read_only_fields = ('status', 'rejection_reason', 'reviewed_by',
                           'reviewed_at', 'submitted_at', 'updated_at')
    
    def validate_document_number(self, value):
        # Basic document number validation
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError('Please enter a valid document number')
        return value