# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    User, UserProfile, Category, Subcategory, Item, Trade,
    TradeMessage, UserBalance, PaymentTransaction, Dispute,
    UserVerification, ItemImage, ItemVariant, ItemOption
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'full_name', 'is_verified', 'is_active', 'date_joined')
    list_filter = ('is_active', 'profile__is_verified', 'date_joined')
    search_fields = ('email', 'username', 'full_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('full_name',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'full_name', 'password1', 'password2'),
        }),
    )
    
    def is_verified(self, obj):
        return obj.profile.is_verified
    is_verified.boolean = True
    is_verified.short_description = 'Verified'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'city', 'is_verified', 'rating', 'completed_trades')
    list_filter = ('is_verified', 'country', 'city')
    search_fields = ('user__email', 'user__username', 'phone_number', 'city')
    raw_id_fields = ('user',)


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_balance', 'normal_balance', 'pending_balance', 'total_withdrawn')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('total_balance',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'is_active', 'sort_order')
    list_filter = ('category_type', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'category__name')
    prepopulated_fields = {'slug': ('name',)}


class ItemImageInline(admin.TabularInline):
    model = ItemImage
    extra = 1
    fields = ('image', 'is_primary', 'caption', 'sort_order')


class ItemVariantInline(admin.TabularInline):
    model = ItemVariant
    extra = 1
    fields = ('name', 'value', 'additional_price', 'quantity')


class ItemOptionInline(admin.TabularInline):
    model = ItemOption
    extra = 1
    fields = ('name', 'value', 'additional_price')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'trade_type', 'price', 'status', 'created_at')
    list_filter = ('status', 'trade_type', 'category', 'created_at')
    search_fields = ('title', 'description', 'user__email', 'user__username')
    readonly_fields = ('views', 'created_at', 'updated_at', 'expires_at')
    inlines = [ItemImageInline, ItemVariantInline, ItemOptionInline]
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'title', 'slug', 'description')
        }),
        ('Category', {
            'fields': ('category', 'subcategory')
        }),
        ('Pricing', {
            'fields': ('price', 'price_unit', 'negotiable', 'trade_type')
        }),
        ('Quantity', {
            'fields': ('quantity', 'min_order_quantity')
        }),
        ('Location', {
            'fields': ('location', 'city', 'state', 'country', 'latitude', 'longitude')
        }),
        ('Rental Details', {
            'fields': ('rental_period', 'min_rental_days', 'deposit_required'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'is_featured', 'views', 'expires_at')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class TradeMessageInline(admin.TabularInline):
    model = TradeMessage
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('sender', 'message', 'is_read', 'created_at')


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('trade_id', 'buyer', 'seller', 'item', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'is_paid')
    search_fields = ('trade_id', 'buyer__email', 'seller__email', 'item__title')
    readonly_fields = ('trade_id', 'created_at', 'updated_at', 'completed_at')
    inlines = [TradeMessageInline]
    fieldsets = (
        ('Trade Info', {
            'fields': ('trade_id', 'buyer', 'seller', 'item')
        }),
        ('Details', {
            'fields': ('quantity', 'unit_price', 'total_amount', 'selected_variants', 'selected_options')
        }),
        ('Status', {
            'fields': ('status', 'is_paid')
        }),
        ('Ratings', {
            'fields': ('buyer_rating', 'seller_rating', 'buyer_feedback', 'seller_feedback'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('status', 'transaction_type', 'payment_method', 'created_at')
    search_fields = ('reference', 'user__email', 'gateway_reference')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    fieldsets = (
        ('Transaction', {
            'fields': ('reference', 'user', 'transaction_type', 'amount', 'status')
        }),
        ('Payment Method', {
            'fields': ('payment_method', 'gateway_reference', 'gateway_response')
        }),
        ('Related Objects', {
            'fields': ('trade',)
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_number', 'account_name', 'details'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ('id', 'trade', 'opened_by', 'status', 'resolution', 'created_at')
    list_filter = ('status', 'resolution', 'created_at')
    search_fields = ('trade__trade_id', 'opened_by__email', 'reason')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at')
    fieldsets = (
        ('Dispute Info', {
            'fields': ('trade', 'opened_by', 'reason', 'description', 'evidence')
        }),
        ('Resolution', {
            'fields': ('status', 'resolution', 'resolution_notes', 'resolved_by', 'resolved_at')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(UserVerification)
class UserVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'submitted_at', 'reviewed_at')
    list_filter = ('status', 'document_type', 'submitted_at')
    search_fields = ('user__email', 'document_number')
    readonly_fields = ('submitted_at', 'updated_at', 'reviewed_at')
    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Document Details', {
            'fields': ('document_type', 'document_number')
        }),
        ('Document Images', {
            'fields': ('front_image', 'back_image', 'selfie_image')
        }),
        ('Review Status', {
            'fields': ('status', 'rejection_reason', 'reviewed_by', 'reviewed_at')
        }),
        ('Dates', {
            'fields': ('submitted_at', 'updated_at')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status != 'pending':
            return self.readonly_fields + ('document_type', 'document_number', 'front_image', 'back_image', 'selfie_image')
        return self.readonly_fields


@admin.register(TradeMessage)
class TradeMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'trade', 'sender', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('trade__trade_id', 'sender__email', 'message')
    readonly_fields = ('created_at',)


# Register remaining models with basic admin
admin.site.register(ItemImage)
admin.site.register(ItemVariant)
admin.site.register(ItemOption)