from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from .models import InvestmentTier, Investment, Wallet, Referral, IPAddress, CustomUser, Deposit, ReferralReward, Withdrawal, DailySpecial, Voucher, AdminActivityLog, ChatUsage
from django.contrib import messages
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from datetime import timedelta, datetime
from decimal import Decimal
from django.db.models import Sum
from django.http import JsonResponse
from django.urls import reverse
import random
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from .forms import VoucherForm
import logging

# Home view
# Landing page for the application
def home_view(request):
    # Get investment tiers
    investment_tiers = InvestmentTier.objects.all().order_by('amount')
    
    # Get platform stats
    total_investors = CustomUser.objects.count()
    total_payouts = Investment.objects.filter(is_active=False).aggregate(
        total=Sum('return_amount')
    )['total'] or 0
    ai_strategies = 5  # Mock value for now
    
    # Get top referrers
    top_referrers = CustomUser.objects.annotate(
        total_earnings=Sum('rewards__reward_amount')
    ).filter(total_earnings__isnull=False).order_by('-total_earnings')[:3]
    
    # Generate referral link for authenticated users
    referral_link = None
    if request.user.is_authenticated:
        referral_link = request.build_absolute_uri(
            reverse('register') + f'?ref={request.user.username}'
        )
    
    # Mock testimonials (replace with real data later)
    testimonials = [
        {
            'name': 'John D.',
            'content': 'I turned R50 into R75 in just 7 days. This platform works!'
        },
        {
            'name': 'Sarah M.',
            'content': 'The AI trading system is impressive. My investments are growing steadily.'
        },
        {
            'name': 'Michael T.',
            'content': 'Best crypto investment platform I\'ve used. The returns are consistent.'
        }
    ]
    
    context = {
        'investment_tiers': investment_tiers,
        'total_investors': total_investors,
        'total_payouts': total_payouts,
        'ai_strategies': ai_strategies,
        'top_referrers': top_referrers,
        'referral_link': referral_link,
        'testimonials': testimonials,
    }
    
    return render(request, 'core/home.html', context)

# Registration view
# Handles user registration
def register_view(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('register')
            
        try:
            first_name, last_name = full_name.split(' ', 1) if ' ' in full_name else (full_name, '')
            user = CustomUser.objects.create_user(
                username=email,
                email=email,
                password=password,
                phone=phone,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create a wallet for the user
            Wallet.objects.create(user=user)
            
            # Handle referral code
            ref_code = request.GET.get('ref')
            if ref_code:
                try:
                    referrer = CustomUser.objects.get(username=ref_code)
                    Referral.objects.create(inviter=referrer, invitee=user)
                except CustomUser.DoesNotExist:
                    pass
            
            # Log the user in
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to AI Crypto Vault.')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, 'An error occurred during registration. Please try again.')
            return redirect('register')
            
    return render(request, 'core/register.html')

# Login view
# Handles user login
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'core/login.html')

# Dashboard view
# Shows user balance, investments, and referral stats
@login_required
def dashboard_view(request):
    user = request.user
    # Get or create wallet for the user
    wallet, created = Wallet.objects.get_or_create(user=user)
    investments = Investment.objects.filter(user=user)
    deposits = Deposit.objects.filter(user=user).order_by('-created_at')
    referrals = Referral.objects.filter(inviter=user)
    
    # Get referral rewards
    referral_rewards = ReferralReward.objects.filter(referrer=user)
    total_referral_earnings = referral_rewards.aggregate(total=Sum('reward_amount'))['total'] or 0
    
    # Calculate total earnings from investments
    total_investment_earnings = sum(inv.return_amount - inv.amount for inv in investments if not inv.is_active)
    
    # Calculate total earnings
    total_earnings = total_investment_earnings + total_referral_earnings
    
    # Calculate total expected return from active investments
    active_investments = investments.filter(is_active=True)
    total_expected_return = sum(inv.return_amount for inv in active_investments)
    
    # Calculate max waiting time (days until the furthest end date)
    max_waiting_time = 0
    if active_investments.exists():
        furthest_end_date = max(inv.end_date for inv in active_investments)
        max_waiting_time = (furthest_end_date - timezone.now()).days
    
    # Calculate total deposits
    total_deposits = sum(dep.amount for dep in deposits if dep.status == 'approved')
    
    # Calculate total bonus from referrals
    total_bonus = total_referral_earnings
    
    # Get active and completed investments
    active_investments = investments.filter(is_active=True)
    completed_investments = investments.filter(is_active=False)
    
    # Get available tiers for user's level
    available_tiers = InvestmentTier.objects.filter(min_level__lte=user.level)
    
    # Calculate progress to next level
    next_level_threshold = user.get_next_level_threshold()
    progress_percentage = 0
    if next_level_threshold > 0:
        if user.level == 1:
            progress_percentage = (user.total_invested / Decimal('10000')) * 100
        elif user.level == 2:
            progress_percentage = ((user.total_invested - Decimal('10000')) / Decimal('10000')) * 100
    
    context = {
        'wallet': wallet,
        'total_earnings': total_earnings,
        'total_expected_return': total_expected_return,
        'max_waiting_time': max_waiting_time,
        'total_deposits': total_deposits,
        'total_bonus': total_bonus,
        'active_investments': active_investments,
        'completed_investments': completed_investments,
        'deposits': deposits,
        'tiers': available_tiers,
        'user_level': user.level,
        'total_invested': user.total_invested,
        'next_level_threshold': next_level_threshold,
        'progress_percentage': progress_percentage,
    }
    
    return render(request, 'core/dashboard.html', context)

# Tiers view
# Lists all available investment tiers
@login_required
def tiers_view(request):
    user = request.user
    tiers = InvestmentTier.objects.all()
    
    # Get active daily special
    now = timezone.now()
    try:
        daily_special = DailySpecial.objects.filter(
            is_active=True,
            start_time__lte=now,
            end_time__gte=now
        ).latest('start_time')
    except DailySpecial.DoesNotExist:
        daily_special = None
    
    # Calculate total invested from actual investments
    total_invested = sum(inv.amount for inv in Investment.objects.filter(user=user))
    
    # Get or create user's wallet
    wallet, created = Wallet.objects.get_or_create(user=user)
    
    # Add eligibility and lock status to each tier
    for tier in tiers:
        tier.eligible = tier.min_level <= user.level
        # Get active investment for this tier if it exists
        investment = Investment.objects.filter(user=user, tier=tier, is_active=True).first()
        
        # Check if the active investment is now complete
        if investment and investment.is_complete():
            investment.is_active = False
            investment.save()
            investment = None # It's no longer active
            
        tier.is_active = investment is not None
        tier.invested = tier.is_active or Investment.objects.filter(user=user, tier=tier).exists()

        # Display investment details (active or most recent completed)
        investment_to_display = investment or Investment.objects.filter(user=user, tier=tier).order_by('-end_date').first()

        tier.has_sufficient_balance = wallet.balance >= tier.amount
        if not tier.has_sufficient_balance:
            tier.remaining_amount = tier.amount - wallet.balance
        
        if investment_to_display:
            # Check if investment is complete
            if investment_to_display.is_complete() and investment_to_display.is_active:
                investment_to_display.is_active = False
                investment_to_display.save()
            
            time_remaining = investment_to_display.end_date - timezone.now()
            tier.waiting_time_days = max(0, time_remaining.days)
            tier.waiting_time_hours = max(0, time_remaining.seconds // 3600)
            tier.waiting_time_minutes = max(0, (time_remaining.seconds % 3600) // 60)
            tier.waiting_time_seconds = max(0, time_remaining.seconds % 60)
            tier.can_cash_out = not investment_to_display.is_active and investment_to_display.end_date <= timezone.now()
        # Check if this tier is the daily special
        if daily_special and daily_special.tier == tier:
            tier.is_daily_special = True
            tier.special_return_multiplier = daily_special.special_return_multiplier
            tier.special_return_amount = daily_special.special_return_amount
        else:
            tier.is_daily_special = False
    
    context = {
        'tiers': tiers,
        'user_level': user.level,
        'total_invested': total_invested,
        'daily_special': daily_special,
        'wallet_balance': wallet.balance,
    }
    return render(request, 'core/tiers.html', context)

# Invest view
# Allows user to invest in a tier
@login_required
def invest_view(request, tier_id):
    try:
        user = request.user
        tier = InvestmentTier.objects.get(id=tier_id)
        
        # Check if user's level allows this tier
        if user.level < tier.min_level:
            messages.error(request, f'You need to be level {tier.min_level} to invest in this tier.')
            return redirect('tiers')
        
        # Get or create wallet for the user
        wallet, created = Wallet.objects.get_or_create(user=user)
        
        # Check if user has sufficient balance
        if wallet.balance < tier.amount:
            messages.error(request, 'Insufficient balance. Please make a deposit first.')
            return redirect('tiers')
        
        # Check if user already has an active investment in this tier
        existing_investment = Investment.objects.filter(
            user=user,
            tier=tier,
            is_active=True
        ).first()
        
        if existing_investment:
            messages.error(request, f'You already have an active investment in {tier.name}.')
            return redirect('tiers')
        
        if request.method == 'POST':
            try:
                # Create investment
                start_date = timezone.now()
                end_date = start_date + timedelta(days=tier.duration_days)
                investment = Investment.objects.create(
                    user=user,
                    tier=tier,
                    amount=tier.amount,
                    return_amount=tier.return_amount,
                    start_date=start_date,  # Explicitly set start_date
                    end_date=end_date,
                    expires_at=end_date  # Set expires_at to the same value as end_date
                )
                
                # Update wallet balance - ensure we're using a new query to get the latest data
                wallet = Wallet.objects.get(user=user)
                wallet.balance -= tier.amount
                wallet.save()
                
                messages.success(request, f'Successfully invested R{tier.amount} in {tier.name}.')
                return redirect('dashboard')
            except Exception as e:
                # Log the error for debugging
                print(f"Error processing investment: {str(e)}")
                messages.error(request, f'An error occurred while processing your investment: {str(e)}')
                return render(request, 'core/invest.html', {'tier': tier, 'error': str(e)})
        
        # For GET request, show the investment confirmation page
        return render(request, 'core/invest.html', {'tier': tier})
        
    except InvestmentTier.DoesNotExist:
        messages.error(request, 'Invalid investment tier.')
        return redirect('tiers')
    except Exception as e:
        # Catch any other exceptions
        print(f"Unexpected error in invest_view: {str(e)}")
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('tiers')

# Wallet view
# Shows wallet balance and withdrawal option
@login_required
def wallet_view(request):
    try:
        user = request.user
        # Get or create wallet for the user
        wallet, created = Wallet.objects.get_or_create(user=user)
        
        # Get all transactions
        deposits = Deposit.objects.filter(user=user).order_by('-created_at')
        withdrawals = Withdrawal.objects.filter(user=user).order_by('-created_at')
        investments = Investment.objects.filter(user=user).order_by('-created_at')
        vouchers = Voucher.objects.filter(user=user).order_by('-created_at')
        
        # Combine all transactions into a single list
        transactions = []
        
        # Add deposits
        for deposit in deposits:
            transactions.append({
                'created_at': deposit.created_at,
                'transaction_type': 'deposit',
                'amount': deposit.amount,
                'status': deposit.status,
                'description': f'Deposit via {deposit.payment_method}'
            })
        
        # Add withdrawals
        for withdrawal in withdrawals:
            transactions.append({
                'created_at': withdrawal.created_at,
                'transaction_type': 'withdrawal',
                'amount': withdrawal.amount,
                'status': withdrawal.status,
                'description': f'Withdrawal via {withdrawal.payment_method}'
            })
        
        # Add voucher deposits
        for voucher in vouchers:
            transactions.append({
                'created_at': voucher.created_at,
                'transaction_type': 'Voucher Deposit',
                'amount': voucher.amount,
                'status': voucher.status,
                'description': 'Voucher Deposit'
            })

        # Add investments
        for investment in investments:
            transactions.append({
                'created_at': investment.created_at,
                'transaction_type': 'investment',
                'amount': investment.amount,
                'status': 'Active' if investment.is_active else 'Completed',
                'description': f'Investment in {investment.tier.name}'
            })
            
            # Add returns for completed investments
            if not investment.is_active and investment.end_date:
                transactions.append({
                    'created_at': investment.end_date,
                    'transaction_type': 'return',
                    'amount': investment.return_amount,
                    'status': 'Completed',
                    'description': f'Return from {investment.tier.name}'
                })
        
        # Sort transactions by date (newest first)
        transactions.sort(key=lambda x: x['created_at'], reverse=True)
        
        context = {
            'wallet': wallet,
            'transactions': transactions,
        }
        return render(request, 'core/wallet.html', context)
    except Exception as e:
        logging.error(f"Error in wallet_view for user {request.user.email}: {e}", exc_info=True)
        # Optionally, you can render an error page or return a generic error response
        # For now, let's re-raise to see the error in production logs,
        # but in a real-world scenario, you might handle it differently.
        raise

# Referral view
# Shows referral link and stats
@login_required
def referral_view(request):
    user = request.user
    referrals = Referral.objects.filter(inviter=user)
    total_bonus = sum(ref.bonus_amount for ref in referrals)
    
    # Generate the full referral link
    referral_link = request.build_absolute_uri(
        reverse('register') + f'?ref={user.username}'
    )
    
    context = {
        'referrals': referrals,
        'total_bonus': total_bonus,
        'referral_link': referral_link,  # Pass the full referral link
        'total_referrals': referrals.count(),
        'active_referrals': referrals.filter(status='active').count(),
        'total_earnings': total_bonus,
        'referral_commission': 10,  # 10% commission rate
    }
    return render(request, 'core/referral.html', context)

# Profile view
# Shows and allows editing of user profile
@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        full_name = request.POST.get('full_name')
        
        # Split full_name into first_name and last_name
        if full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''

        user.email = request.POST.get('email')
        user.phone = request.POST.get('phone')
        user.auto_reinvest = request.POST.get('auto_reinvest') == 'on'
        
        # Handle profile picture upload
        if request.FILES.get('profile_picture'):
            user.profile_picture = request.FILES['profile_picture']

        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    return render(request, 'core/profile.html')

@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Verify current password
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('profile')
        
        # Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('profile')
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to prevent logout
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Password changed successfully.')
        return redirect('profile')
    
    return redirect('profile')

# Logout view
# Handles user logout
@login_required
def logout_view(request):
    logout(request)
    return redirect('home')

# Deposit view
# Handles deposit creation
@login_required
def deposit_view(request):
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        payment_method = request.POST.get('payment_method')
        proof_image = request.FILES.get('proof_image')
        
        if amount < 50:
            messages.error(request, 'Minimum deposit amount is R50.')
            return redirect('deposit')
        
        Deposit.objects.create(
            user=request.user,
            amount=amount,
            payment_method=payment_method,
            proof_image=proof_image
        )
        
        messages.success(request, 'Deposit request submitted successfully. Please wait for approval.')
        return redirect('wallet')
        
    return render(request, 'core/deposit.html')

@login_required
def withdrawal_view(request):
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        payment_method = request.POST.get('payment_method')
        
        if amount < 50:
            messages.error(request, 'Minimum withdrawal amount is R50.')
            return redirect('withdrawal')
        
        # Check if user has sufficient balance
        wallet = Wallet.objects.get(user=request.user)
        if wallet.balance < amount:
            messages.error(request, 'Insufficient balance for withdrawal.')
            return redirect('withdrawal')
        
        try:
            withdrawal_data = {
                'user': request.user,
                'amount': amount,
                'payment_method': payment_method,
            }
            
            # Add bank details if payment method is bank transfer
            if payment_method == 'bank':
                withdrawal_data.update({
                    'account_holder_name': request.POST.get('account_holder_name', ''),
                    'bank_name': request.POST.get('bank_name', ''),
                    'account_number': request.POST.get('account_number', ''),
                    'branch_code': request.POST.get('branch_code', ''),
                    'account_type': request.POST.get('account_type', ''),
                })
            
            Withdrawal.objects.create(**withdrawal_data)
            messages.success(request, 'Withdrawal request submitted successfully. Please wait for approval.')
            return redirect('wallet')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('withdrawal')
        
    return render(request, 'core/withdrawal.html')

# Feed view
# Shows real-time activity and AI investment updates
@login_required
def feed_view(request):
    try:
        # --- 1. AI INVESTMENT UPDATES ---
        investment_updates = [
            {
                'message': 'AI Trading Bot completed 5 successful trades',
                'timestamp': timezone.now() - timedelta(minutes=random.randint(1, 5))
            },
            {
                'message': 'Market analysis shows positive trends for BTC',
                'timestamp': timezone.now() - timedelta(minutes=random.randint(6, 10))
            },
            {
                'message': 'New trading strategy implemented successfully',
                'timestamp': timezone.now() - timedelta(minutes=random.randint(11, 15))
            },
            {
                'message': 'AI detected profitable arbitrage opportunity',
                'timestamp': timezone.now() - timedelta(minutes=random.randint(16, 20))
            },
            {
                'message': 'Portfolio rebalancing completed for optimal returns',
                'timestamp': timezone.now() - timedelta(minutes=random.randint(21, 25))
            }
        ]

        # --- 2. USER MILESTONES ---
        user_milestones = [
            {
                'type': 'deposit',
                'user': 'CryptoKing',
                'amount': random.randint(1000, 10000),
                'timestamp': timezone.now() - timedelta(minutes=random.randint(1, 5))
            },
            {
                'type': 'deposit',
                'user': 'TraderPro',
                'amount': random.randint(1000, 10000),
                'timestamp': timezone.now() - timedelta(minutes=random.randint(6, 10))
            },
            {
                'type': 'upgrade',
                'user': 'BitcoinWhale',
                'level': random.randint(2, 5),
                'timestamp': timezone.now() - timedelta(minutes=random.randint(11, 15))
            },
            {
                'type': 'payout',
                'user': 'CryptoMaster',
                'amount': random.randint(1000, 10000),
                'timestamp': timezone.now() - timedelta(minutes=random.randint(16, 20))
            },
            {
                'type': 'deposit',
                'user': 'AltcoinTrader',
                'amount': random.randint(1000, 10000),
                'timestamp': timezone.now() - timedelta(minutes=random.randint(21, 25))
            }
        ]

        # --- 3. REFERRAL ACTIVITY ---
        referral_activities = [
            {
                'referrer': 'MasterTrader',
                'referred': 'NewUser123',
                'amount': random.randint(10, 50),
                'timestamp': timezone.now() - timedelta(minutes=random.randint(1, 5))
            },
            {
                'referrer': 'CryptoPro',
                'referred': 'Investor456',
                'amount': random.randint(10, 50),
                'timestamp': timezone.now() - timedelta(minutes=random.randint(6, 10))
            },
            {
                'referrer': 'BitcoinKing',
                'referred': 'Trader789',
                'amount': random.randint(10, 50),
                'timestamp': timezone.now() - timedelta(minutes=random.randint(11, 15))
            },
            {
                'referrer': 'AltcoinMaster',
                'referred': 'CryptoNewbie',
                'amount': random.randint(10, 50),
                'timestamp': timezone.now() - timedelta(minutes=random.randint(16, 20))
            },
            {
                'referrer': 'TradingGuru',
                'referred': 'FutureTrader',
                'amount': random.randint(10, 50),
                'timestamp': timezone.now() - timedelta(minutes=random.randint(21, 25))
            }
        ]

        # --- 4. TIPS & SECURITY REMINDERS ---
        tips = [
            "💡 Tip: Reinvest to reach higher tiers faster.",
            "💡 Tip: Refer friends to earn passive income.",
            "💡 Tip: Higher tiers offer better returns.",
            "💡 Tip: Stay consistent with your investments.",
            "💡 Tip: Monitor market trends for better timing."
        ]
        
        security_reminders = [
            "⚠️ We never ask for your private keys. Stay safe.",
            "⚠️ Enable 2FA for extra security.",
            "⚠️ Keep your login credentials private.",
            "⚠️ Verify all transactions carefully.",
            "⚠️ Report suspicious activity immediately."
        ]
        
        # --- 5. DAILY STATS ---
        daily_stats = {
            'total_users': random.randint(1000, 1500),
            'active_investments': random.randint(800, 1000),
            'total_deposits': random.randint(2000000, 3000000),
            'total_payouts': random.randint(1500000, 2000000),
            'success_rate': random.uniform(95.0, 99.9)
        }

        context = {
            'investment_updates': investment_updates,
            'user_milestones': user_milestones,
            'referral_activities': referral_activities,
            'tips': tips,
            'security_reminders': security_reminders,
            'daily_stats': daily_stats,
            'last_update': timezone.now().isoformat(),
            'status': 'success'
        }
        
        return render(request, 'core/feed.html', context)
        
    except Exception as e:
        # Log the error for debugging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in feed_view: {str(e)}", exc_info=True)
        
        # Return a user-friendly error context
        error_context = {
            'status': 'error',
            'error_message': 'Unable to load feed data. Please try again later.',
            'investment_updates': [],
            'user_milestones': [],
            'referral_activities': [],
            'tips': ["💡 Tip: If you're seeing this message, please refresh the page."],
            'security_reminders': ["⚠️ We're experiencing technical difficulties. Please try again later."],
            'daily_stats': {
                'total_users': 'N/A',
                'active_investments': 'N/A',
                'total_deposits': 'N/A',
                'total_payouts': 'N/A',
                'success_rate': 'N/A'
            }
        }
        return render(request, 'core/feed.html', error_context)

@login_required
def cash_out_view(request, investment_id):
    try:
        investment = Investment.objects.get(id=investment_id, user=request.user)
        
        # Check if investment is ready for cash out
        if investment.is_active or investment.end_date > timezone.now():
            messages.error(request, 'This investment is not ready for cash out yet.')
            return redirect('tiers')
        
        # Get user's wallet
        wallet = Wallet.objects.get(user=request.user)
        
        # Add return amount to wallet balance
        wallet.balance += investment.return_amount
        wallet.save()
        
        # Mark investment as cashed out
        investment.is_active = False
        investment.save()
        
        messages.success(request, f'Successfully cashed out R{investment.return_amount}.')
        return redirect('tiers')
        
    except Investment.DoesNotExist:
        messages.error(request, 'Invalid investment.')
        return redirect('tiers')

@login_required
def check_cash_out_view(request, investment_id):
    try:
        investment = Investment.objects.get(id=investment_id, user=request.user)
        can_cash_out = not investment.is_active and investment.end_date <= timezone.now()
        
        return JsonResponse({
            'can_cash_out': can_cash_out,
            'return_amount': str(investment.return_amount) if can_cash_out else None
        })
    except Investment.DoesNotExist:
        return JsonResponse({'error': 'Invalid investment'}, status=404)

@login_required
def get_server_time_view(request):
    return JsonResponse({
        'server_time': timezone.now().isoformat()
    })

def newsletter_subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # Here you would typically save the email to your newsletter subscribers list
            # For now, we'll just show a success message
            messages.success(request, 'Thank you for subscribing to our newsletter!')
        else:
            messages.error(request, 'Please provide a valid email address.')
    return redirect('home')

def terms_view(request):
    return render(request, 'core/terms.html')

def privacy_view(request):
    return render(request, 'core/privacy.html')

def contact_view(request):
    if request.method == 'POST':
        # Here you would typically handle the contact form submission
        # For now, we'll just show a success message
        messages.success(request, 'Thank you for your message. We will get back to you soon!')
        return redirect('contact')
    return render(request, 'core/contact.html')

def tutorial_view(request):
    return render(request, 'core/tutorial.html')

@staff_member_required
def admin_dashboard_view(request):
    # Get all tiers
    tiers = InvestmentTier.objects.all().order_by('amount')
    
    # Get investment statistics for each tier
    tier_stats = []
    for tier in tiers:
        # Get total number of investments for this tier
        total_investments = Investment.objects.filter(tier=tier).count()
        
        # Get total amount invested in this tier
        total_invested = Investment.objects.filter(tier=tier).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Get total returns for this tier
        total_returns = Investment.objects.filter(tier=tier).aggregate(
            total=Sum('return_amount')
        )['total'] or 0
        
        # Get active investments count
        active_investments = Investment.objects.filter(
            tier=tier,
            is_active=True
        ).count()
        
        # Get completed investments count
        completed_investments = Investment.objects.filter(
            tier=tier,
            is_active=False
        ).count()
        
        # Get unique investors count for this tier
        unique_investors = Investment.objects.filter(tier=tier).values('user').distinct().count()
        
        tier_stats.append({
            'tier': tier,
            'total_investments': total_investments,
            'total_invested': total_invested,
            'total_returns': total_returns,
            'active_investments': active_investments,
            'completed_investments': completed_investments,
            'unique_investors': unique_investors,
        })
    
    # Get overall statistics
    total_deposits = Deposit.objects.filter(status='approved').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    total_investments = Investment.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    total_returns = Investment.objects.filter(is_active=False).aggregate(
        total=Sum('return_amount')
    )['total'] or 0
    
    total_users = CustomUser.objects.count()
    
    # Get detailed user information
    users = CustomUser.objects.all().order_by('-date_joined')
    user_details = []
    
    for user in users:
        # Get user's wallet
        wallet = Wallet.objects.filter(user=user).first()
        
        # Get user's deposits
        deposits = Deposit.objects.filter(user=user).order_by('-created_at')
        total_deposited = deposits.filter(status='approved').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Get user's investments
        investments = Investment.objects.filter(user=user)
        total_invested = investments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Get user's returns
        total_returns = investments.filter(is_active=False).aggregate(
            total=Sum('return_amount')
        )['total'] or 0
        
        # Get user's active investments
        active_investments = investments.filter(is_active=True)
        
        # Get user's referral earnings
        referral_earnings = ReferralReward.objects.filter(referrer=user).aggregate(
            total=Sum('reward_amount')
        )['total'] or 0
        
        # Get user's referrals
        referrals = Referral.objects.filter(inviter=user)
        
        user_details.append({
            'user': user,
            'wallet': wallet,
            'total_deposited': total_deposited,
            'total_invested': total_invested,
            'total_returns': total_returns,
            'active_investments': active_investments,
            'referral_earnings': referral_earnings,
            'total_referrals': referrals.count(),
            'deposits': deposits,
            'investments': investments,
            'referrals': referrals,
        })
    
    # Get recent activities
    recent_deposits = Deposit.objects.all().order_by('-created_at')[:10]
    recent_investments = Investment.objects.all().order_by('-created_at')[:10]
    recent_returns = Investment.objects.filter(is_active=False).order_by('-end_date')[:10]
    
    context = {
        'tier_stats': tier_stats,
        'total_deposits': total_deposits,
        'total_investments': total_investments,
        'total_returns': total_returns,
        'total_users': total_users,
        'user_details': user_details,
        'recent_deposits': recent_deposits,
        'recent_investments': recent_investments,
        'recent_returns': recent_returns,
    }
    
    return render(request, 'core/admin_dashboard.html', context)

@login_required
def portfolio_view(request):
    user = request.user
    
    # Get user's active investments
    active_investments = Investment.objects.filter(
        user=user,
        is_active=True
    ).select_related('tier').order_by('-created_at')
    
    # Get user's completed investments
    completed_investments = Investment.objects.filter(
        user=user,
        is_active=False
    ).select_related('tier').order_by('-end_date')
    
    # Calculate total portfolio value
    total_invested = sum(inv.amount for inv in active_investments)
    total_expected_return = sum(inv.return_amount for inv in active_investments)
    total_earned = sum(inv.return_amount for inv in completed_investments)
    
    # Get investment distribution by tier
    tier_distribution = {}
    for investment in active_investments:
        tier_name = investment.tier.name
        if tier_name in tier_distribution:
            tier_distribution[tier_name] += investment.amount
        else:
            tier_distribution[tier_name] = investment.amount
    
    context = {
        'active_investments': active_investments,
        'completed_investments': completed_investments,
        'total_invested': total_invested,
        'total_expected_return': total_expected_return,
        'total_earned': total_earned,
        'tier_distribution': tier_distribution,
    }
    
    return render(request, 'core/portfolio.html', context)

@login_required
def delete_account(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        
        # Verify password
        if not request.user.check_password(password):
            messages.error(request, 'Incorrect password.')
            return redirect('profile')
        
        # Delete user's wallet and related data
        try:
            wallet = Wallet.objects.get(user=request.user)
            wallet.delete()
        except Wallet.DoesNotExist:
            pass
        
        # Delete user's investments
        Investment.objects.filter(user=request.user).delete()
        
        # Delete user's deposits
        Deposit.objects.filter(user=request.user).delete()
        
        # Delete user's withdrawals
        Withdrawal.objects.filter(user=request.user).delete()
        
        # Delete user's referrals
        Referral.objects.filter(inviter=request.user).delete()
        
        # Delete the user
        user = request.user
        logout(request)
        user.delete()
        
        messages.success(request, 'Your account has been successfully deleted.')
        return redirect('home')
    
    return redirect('profile')

@login_required
def voucher_deposit(request):
    if request.method == 'POST':
        form = VoucherForm(request.POST, request.FILES)
        if form.is_valid():
            voucher = form.save(commit=False)
            voucher.user = request.user
            voucher.save()
            messages.success(request, 'Your voucher has been submitted and is pending approval.')
            return redirect('dashboard')
    else:
        form = VoucherForm()
    return render(request, 'core/voucher_deposit.html', {'form': form})

def support_view(request):
    pass
    # ... existing code ...

# Admin action views for deposit management
@staff_member_required
def admin_approve_deposit(request, deposit_id):
    """Quick approve a deposit from admin interface"""
    try:
        deposit = Deposit.objects.get(id=deposit_id)
        
        if deposit.status != 'pending':
            messages.error(request, f'Deposit {deposit_id} is not pending approval.')
            return redirect('admin:core_deposit_changelist')
        
        # Validate deposit before approval
        if not deposit.proof_image:
            messages.error(request, f'Deposit {deposit_id} has no proof image - cannot approve.')
            return redirect('admin:core_deposit_changelist')
        
        # Approve the deposit
        deposit.status = 'approved'
        deposit.admin_notes += f'\nQuick approved by {request.user.username} on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        deposit.save()
        
        # Log admin activity
        AdminActivityLog.objects.create(
            admin_user=request.user,
            action='Quick Approved Deposit',
            target_model='Deposit',
            target_id=deposit.id,
            details=f'Quick approved deposit of R{deposit.amount} for user {deposit.user.username}'
        )
        
        messages.success(request, f'Successfully approved deposit R{deposit.amount} for {deposit.user.username}.')
        
    except Deposit.DoesNotExist:
        messages.error(request, f'Deposit {deposit_id} not found.')
    except Exception as e:
        messages.error(request, f'Error approving deposit: {str(e)}')
    
    return redirect('admin:core_deposit_changelist')

@staff_member_required
def admin_reject_deposit(request, deposit_id):
    """Quick reject a deposit from admin interface"""
    try:
        deposit = Deposit.objects.get(id=deposit_id)
        
        if deposit.status != 'pending':
            messages.error(request, f'Deposit {deposit_id} is not pending approval.')
            return redirect('admin:core_deposit_changelist')
        
        # Reject the deposit
        deposit.status = 'rejected'
        deposit.admin_notes += f'\nQuick rejected by {request.user.username} on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        deposit.save()
        
        # Log admin activity
        AdminActivityLog.objects.create(
            admin_user=request.user,
            action='Quick Rejected Deposit',
            target_model='Deposit',
            target_id=deposit.id,
            details=f'Quick rejected deposit of R{deposit.amount} for user {deposit.user.username}'
        )
        
        messages.success(request, f'Successfully rejected deposit R{deposit.amount} for {deposit.user.username}.')
        
    except Deposit.DoesNotExist:
        messages.error(request, f'Deposit {deposit_id} not found.')
    except Exception as e:
        messages.error(request, f'Error rejecting deposit: {str(e)}')
    
    return redirect('admin:core_deposit_changelist')

@staff_member_required
def deposit_dashboard_view(request):
    """Admin dashboard for deposit management"""
    # Get deposit statistics
    pending_deposits = Deposit.objects.filter(status='pending')
    approved_deposits = Deposit.objects.filter(status='approved')
    rejected_deposits = Deposit.objects.filter(status='rejected')
    
    # Calculate amounts
    pending_amount = sum(dep.amount for dep in pending_deposits)
    
    # Get recent admin activity
    recent_activity = AdminActivityLog.objects.filter(
        target_model='Deposit'
    ).order_by('-timestamp')[:10]
    
    context = {
        'pending_count': pending_deposits.count(),
        'approved_count': approved_deposits.count(),
        'rejected_count': rejected_deposits.count(),
        'pending_amount': pending_amount,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'admin/deposit_dashboard.html', context)

@login_required
def chat_ai_api(request):
    """API endpoint for chat AI with rate limiting"""
    if request.method == 'POST':
        user = request.user
        message = request.POST.get('message', '').strip()
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Rate limiting: Check if user has used chat more than 10 times today
        start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        usage_count = ChatUsage.objects.filter(user=user, timestamp__gte=start_of_day).count()
        
        if usage_count >= 10:
            return JsonResponse({'error': 'Daily chat limit reached. Please try again tomorrow.'}, status=429)
        
        # Record this usage
        ChatUsage.objects.create(user=user)
        
        # Simple AI response (replace with actual AI integration)
        ai_responses = [
            "I understand your question about crypto investments. Based on current market trends, I'd recommend diversifying your portfolio.",
            "That's an interesting point about blockchain technology. The market is showing positive signals for long-term growth.",
            "Regarding your investment strategy, I suggest starting with smaller amounts and gradually increasing as you gain experience.",
            "The crypto market can be volatile, so it's important to only invest what you can afford to lose.",
            "I can help you understand the different investment tiers available on our platform. Each has its own risk and return profile."
        ]
        
        response = random.choice(ai_responses)
        
        return JsonResponse({
            'response': response,
            'usage_count': usage_count + 1,
            'daily_limit': 10
        })
    
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

@login_required
def chat_view(request):
    return render(request, 'core/chat.html')
