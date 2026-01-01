# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']
    
    def __str__(self):
        return self.email


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    
    # Verification status
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    # User stats
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_rating_count = models.IntegerField(default=0)
    completed_trades = models.IntegerField(default=0)
    
    # For unverified user limits
    active_ads_count = models.IntegerField(default=0)
    last_ad_posted = models.DateTimeField(null=True, blank=True)
    
    # Favorites
    favorites = models.ManyToManyField('Item', related_name='favorited_by', blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['is_verified']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.user.email}'s Profile"


class UserBalance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='balance')
    normal_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pending_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_withdrawn = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_deposited = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def total_balance(self):
        return self.normal_balance + self.pending_balance
    
    def __str__(self):
        return f"{self.user.email} - Balance: ${self.total_balance}"


class Category(models.Model):
    CATEGORY_TYPES = [
        ('agricultural', 'Agricultural Products'),
        ('farm_items', 'Farm Items'),
        ('planting', 'Planting/Seeding Items'),
        ('food', 'Food Stuffs'),
        ('land', 'Land Rental'),
        ('factory', 'Factory Rental'),
        ('equipment', 'Equipment Sale/Rental'),
        ('livestock', 'Livestock'),
        ('services', 'Agricultural Services'),
        ('others', 'Others'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    category_type = models.CharField(max_length=50, choices=CATEGORY_TYPES)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Subcategories"
        unique_together = ['category', 'slug']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Item(models.Model):
    TRADE_TYPES = [
        ('sale', 'For Sale'),
        ('rental', 'For Rental'),
        ('lease', 'For Lease'),
        ('both', 'Sale or Rental'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('sold', 'Sold'),
        ('rented', 'Rented'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='items')
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, related_name='items')
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField()
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    price_unit = models.CharField(max_length=50, default='unit')  # per kg, per item, per day, etc.
    negotiable = models.BooleanField(default=False)
    
    # Trade details
    trade_type = models.CharField(max_length=20, choices=TRADE_TYPES)
    quantity = models.IntegerField(null=True, blank=True)  # None for unlimited
    min_order_quantity = models.IntegerField(default=1)
    
    # Location
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Nigeria')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Status and dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Rental specific fields
    rental_period = models.CharField(max_length=50, blank=True, null=True)  # daily, weekly, monthly
    min_rental_days = models.IntegerField(null=True, blank=True)
    deposit_required = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
            models.Index(fields=['trade_type', 'status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Item.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        
        if self.status == 'active' and not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        
        super().save(*args, **kwargs)


class ItemImage(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='item_images/')
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=255, blank=True, null=True)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['is_primary', 'sort_order']
    
    def __str__(self):
        return f"Image for {self.item.title}"


class ItemVariant(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)  # e.g., Size, Color, Grade
    value = models.CharField(max_length=100)  # e.g., Large, Red, Grade A
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    quantity = models.IntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ['item', 'name', 'value']
    
    def __str__(self):
        return f"{self.item.title} - {self.name}: {self.value}"


class ItemOption(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100)  # e.g., Delivery, Warranty
    value = models.CharField(max_length=100)  # e.g., Free Delivery, 1 Year
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    class Meta:
        unique_together = ['item', 'name', 'value']
    
    def __str__(self):
        return f"{self.item.title} - {self.name}: {self.value}"


class Trade(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('disputed', 'Disputed'),
        ('refunded', 'Refunded'),
    ]
    
    # Trade identifier
    trade_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    
    # Participants
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='buyer_trades')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seller_trades')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, related_name='trades')
    
    # Trade details
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Variants and options selected
    selected_variants = models.JSONField(default=list, blank=True)  # List of variant IDs
    selected_options = models.JSONField(default=list, blank=True)   # List of option IDs
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_paid = models.BooleanField(default=True)
    
    # Dates
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Rating
    buyer_rating = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    seller_rating = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    buyer_feedback = models.TextField(blank=True, null=True)
    seller_feedback = models.TextField(blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['trade_id']),
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Trade {self.trade_id}: {self.buyer.email} -> {self.seller.email}"
    
    def save(self, *args, **kwargs):
        if not self.trade_id:
            self.trade_id = str(uuid.uuid4())[:8].upper()
        
        # Ensure trade_id is unique
        while Trade.objects.filter(trade_id=self.trade_id).exists():
            self.trade_id = str(uuid.uuid4())[:8].upper()
        
        if not self.unit_price and self.item:
            self.unit_price = self.item.price
        
        if not self.total_amount:
            self.total_amount = self.unit_price * self.quantity
        
        super().save(*args, **kwargs)


class TradeMessage(models.Model):
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['trade', 'created_at']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.email} in Trade {self.trade.trade_id}"


class Dispute(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    RESOLUTION_CHOICES = [
        ('refund_buyer', 'Refund Buyer'),
        ('release_to_seller', 'Release to Seller'),
        ('partial_refund', 'Partial Refund'),
        ('other', 'Other'),
    ]
    
    trade = models.OneToOneField(Trade, on_delete=models.CASCADE, related_name='disputes')
    opened_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='opened_disputes')
    reason = models.CharField(max_length=255)
    description = models.TextField()
    evidence = models.JSONField(default=list, blank=True)  # List of image URLs or documents
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    resolution = models.CharField(max_length=50, choices=RESOLUTION_CHOICES, blank=True, null=True)
    resolution_notes = models.TextField(blank=True, null=True)
    
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_disputes')
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['trade']),
        ]
    
    def __str__(self):
        return f"Dispute for Trade {self.trade.trade_id}"


class PaymentTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('trade_payment', 'Trade Payment'),
        ('trade_release', 'Trade Release'),
        ('refund', 'Refund'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Credit/Debit Card'),
        ('wallet', 'Wallet Balance'),
        ('gateway', 'Payment Gateway'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    # Reference to related objects
    trade = models.ForeignKey(Trade, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    # Payment details
    reference = models.CharField(max_length=100, unique=True)
    gateway_reference = models.CharField(max_length=200, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)
    
    # Bank details for withdrawal
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    account_name = models.CharField(max_length=200, blank=True, null=True)
    
    details = models.JSONField(default=dict, blank=True)  # Additional payment details
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['user', 'transaction_type']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['gateway_reference']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - ${self.amount} - {self.status}"


class UserVerification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    DOCUMENT_TYPES = [
        ('nin', 'National ID Number'),
        ('driver_license', "Driver's License"),
        ('voter_card', 'Voter Card'),
        ('passport', 'International Passport'),
        ('utility_bill', 'Utility Bill'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=100)
    
    # Document uploads
    front_image = models.ImageField(upload_to='verification_documents/')
    back_image = models.ImageField(upload_to='verification_documents/', blank=True, null=True)
    selfie_image = models.ImageField(upload_to='verification_documents/')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_verifications')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    submitted_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Verification for {self.user.email} - {self.status}"