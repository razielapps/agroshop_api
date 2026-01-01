# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    HealthView, UserRegistrationView, UserLoginView, UserProfileView,
    UserBalanceView, RechargeBalanceView, WithdrawalView, CategoryViewSet,
    ItemViewSet, TradeViewSet, DisputeViewSet, UserVerificationView,
    DashboardView, UserAccountView, AdminDashboardView, AdminUserManagementView
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'items', ItemViewSet, basename='item')
router.register(r'trades', TradeViewSet, basename='trade')
router.register(r'disputes', DisputeViewSet, basename='dispute')

urlpatterns = [
    # Health check
    path('health/', HealthView.as_view(), name='health'),
    
    # Authentication
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/login/', UserLoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User management
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('user/balance/', UserBalanceView.as_view(), name='user-balance'),
    path('user/recharge/', RechargeBalanceView.as_view(), name='recharge-balance'),
    path('user/withdraw/', WithdrawalView.as_view(), name='withdraw'),
    path('user/verify/', UserVerificationView.as_view(), name='user-verification'),
    path('user/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('user/account/delete/', UserAccountView.as_view(), name='delete-account'),
    
    # Admin
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/users/manage/', AdminUserManagementView.as_view(), name='admin-user-management'),
    
    # API endpoints
    path('', include(router.urls)),
]