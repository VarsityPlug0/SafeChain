from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('tiers/', views.tiers_view, name='tiers'),
    path('invest/<int:tier_id>/', views.invest_view, name='invest'),
    path('cash-out/<int:investment_id>/', views.cash_out_view, name='cash_out'),
    path('check-cash-out/<int:investment_id>/', views.check_cash_out_view, name='check_cash_out'),
    path('get-server-time/', views.get_server_time_view, name='get_server_time'),
    path('wallet/', views.wallet_view, name='wallet'),
    path('referral/', views.referral_view, name='referral'),
    path('feed/', views.feed_view, name='feed'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('logout/', views.logout_view, name='logout'),
    path('deposit/', views.deposit_view, name='deposit'),
    path('voucher-deposit/', views.voucher_deposit, name='voucher_deposit'),
    path('withdraw/', views.withdrawal_view, name='withdraw'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('terms/', views.terms_view, name='terms'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('contact/', views.contact_view, name='contact'),
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('tutorial/', views.tutorial_view, name='tutorial'),
    path('support/', views.support_view, name='support'),
    path('chat/', views.chat_view, name='chat'),

    # Admin action URLs for deposit management
    path('admin/deposit/<int:deposit_id>/approve/', views.admin_approve_deposit, name='admin_approve_deposit'),
    path('admin/deposit/<int:deposit_id>/reject/', views.admin_reject_deposit, name='admin_reject_deposit'),
    path('admin/deposit-dashboard/', views.deposit_dashboard_view, name='deposit_dashboard'),

    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='core/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='core/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='core/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='core/password_reset_complete.html'), name='password_reset_complete'),
] 