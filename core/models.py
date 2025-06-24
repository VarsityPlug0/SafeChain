from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver

# South African Banks and their branch codes
BANK_CHOICES = [
    ('ABSA', 'ABSA Bank'),
    ('CAPITEC', 'Capitec Bank'),
    ('FNB', 'First National Bank'),
    ('INVESTEC', 'Investec Bank'),
    ('NEDBANK', 'Nedbank'),
    ('STANDARD', 'Standard Bank'),
    ('AFRICAN', 'African Bank'),
    ('BIDVEST', 'Bidvest Bank'),
    ('DISCOVERY', 'Discovery Bank'),
    ('GRINDROD', 'Grindrod Bank'),
    ('HSBC', 'HSBC Bank'),
    ('MERCANTILE', 'Mercantile Bank'),
    ('SAHL', 'South African Home Loans'),
    ('TYM', 'TymeBank'),
    ('UBS', 'UBS Bank'),
]

# Custom user model extending AbstractUser
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    auto_reinvest = models.BooleanField(default=False)
    total_invested = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    level = models.IntegerField(default=1)
    last_ip = models.GenericIPAddressField(null=True, blank=True)  # Last known IP address
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def update_level(self):
        """Update user level based on total investment"""
        if self.total_invested >= Decimal('20000'):
            self.level = 3
        elif self.total_invested >= Decimal('10000'):
            self.level = 2
        else:
            self.level = 1
        self.save()

    def get_next_level_threshold(self):
        """Get the amount needed to reach next level"""
        if self.level == 1:
            return Decimal('10000') - self.total_invested
        elif self.level == 2:
            return Decimal('20000') - self.total_invested
        return Decimal('0')

    def get_available_tiers(self):
        """Get tiers available for user's level"""
        if self.level == 1:
            return [50, 100, 250, 500, 1000]
        elif self.level == 2:
            return [2000, 5000, 7500, 10000]
        else:
            return [20000, 50000]

# Investment tier model (e.g. R50, R200, etc.)
class InvestmentTier(models.Model):
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    return_amount = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.IntegerField()
    min_level = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    logo = models.ImageField(upload_to='tier_logos/', null=True, blank=True)  # Logo for the tier
    description = models.TextField(blank=True)  # Description of the tier

    def __str__(self):
        return f"{self.name} - R{self.amount}"

# Investment model
class Investment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    tier = models.ForeignKey(InvestmentTier, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    return_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=timezone.now)  # Added default value
    is_active = models.BooleanField(default=True)
    profit_paid = models.BooleanField(default=False)  # Track if profit has been paid to wallet
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_complete(self):
        """Check if the investment period is complete"""
        return self.end_date is not None and timezone.now() >= self.end_date

    def save(self, *args, **kwargs):
        # Set end_date when creating a new investment
        if not self.pk:  # Only on creation
            # Ensure start_date is set if it's None
            if not self.start_date:
                self.start_date = timezone.now()
            # Calculate end_date safely
            self.end_date = self.start_date + timezone.timedelta(days=self.tier.duration_days)
            self.user.total_invested += self.amount
            self.user.update_level()
        
        # Check if investment period is complete and profit hasn't been paid yet
        if (self.end_date and self.is_active and timezone.now() >= self.end_date and not self.profit_paid):
            self.is_active = False
            # Automatically add profit to wallet
            wallet, created = Wallet.objects.get_or_create(user=self.user)
            wallet.balance += self.return_amount
            wallet.save()
            self.profit_paid = True
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.tier.name} ({self.amount})"

# Deposit model
class Deposit(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    PAYMENT_METHODS = [
        ('eft', 'EFT'),
        ('cash', 'Cash Deposit'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    proof_image = models.ImageField(upload_to='deposit_proofs/', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_notes = models.TextField(blank=True)  # Admin notes for approval/rejection

    def save(self, *args, **kwargs):
        # If this is an update
        if self.pk:
            try:
                # Get the old instance from the database
                old_instance = Deposit.objects.get(pk=self.pk)
                # If the status is changing from something else to 'approved'
                if old_instance.status != 'approved' and self.status == 'approved':
                    # Get or create the user's wallet and update the balance
                    wallet, created = Wallet.objects.get_or_create(user=self.user)
                    wallet.balance += self.amount
                    wallet.save()
            except Deposit.DoesNotExist:
                # This should not happen if self.pk is set, but handle it just in case
                pass
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - R{self.amount} ({self.status})"

# Withdrawal model
class Withdrawal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    PAYMENT_METHODS = [
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash Withdrawal'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    # Bank details fields
    account_holder_name = models.CharField(max_length=100, blank=True)
    bank_name = models.CharField(max_length=100, choices=BANK_CHOICES, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    branch_code = models.CharField(max_length=20, blank=True)
    account_type = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_notes = models.TextField(blank=True)  # Admin notes for approval/rejection

    def __str__(self):
        return f"{self.user.username} - R{self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        # Get the old instance if this is an update
        if self.pk:
            try:
                old_instance = Withdrawal.objects.get(pk=self.pk)
                # If status is changing to approved
                if old_instance.status != 'approved' and self.status == 'approved':
                    # Get the user's wallet
                    wallet = self.user.wallet
                    if wallet.balance >= self.amount:
                        wallet.balance -= self.amount
                        wallet.save()
                    else:
                        raise ValueError("Insufficient balance for withdrawal")
            except Withdrawal.DoesNotExist:
                pass
        super().save(*args, **kwargs)

# Wallet model (one per user)
class Wallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# Referral model
class Referral(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('inactive', 'Inactive'),
    ]
    
    inviter = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='referrals_made')
    invitee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='referrals_received')
    bonus_amount = models.DecimalField(max_digits=12, decimal_places=2, default=50)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.inviter.username} referred {self.invitee.username}"

    def save(self, *args, **kwargs):
        # Update status to active if invitee has made a deposit
        if self.invitee.deposit_set.filter(status='approved').exists():
            self.status = 'active'
        super().save(*args, **kwargs)

# IP Address log for R50 limit enforcement
class IPAddress(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)  # User associated with IP
    ip_address = models.GenericIPAddressField()  # IP address
    tier = models.ForeignKey('InvestmentTier', on_delete=models.CASCADE)  # Tier (for R50 enforcement)
    created_at = models.DateTimeField(auto_now_add=True)  # When logged

class ReferralReward(models.Model):
    """Model to track referral rewards for successful deposits"""
    referrer = models.ForeignKey(CustomUser, related_name='rewards', on_delete=models.CASCADE)
    referred = models.ForeignKey(CustomUser, related_name='referred_rewards', on_delete=models.CASCADE)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    awarded_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    class Meta:
        unique_together = ('referrer', 'referred')
        ordering = ['-awarded_at']

    def __str__(self):
        return f"R{self.reward_amount} reward for {self.referrer.username} from {self.referred.username}"

    def save(self, *args, **kwargs):
        # The logic to credit the wallet is now handled by the create_referral_reward signal.
        # This save method is now standard.
        super().save(*args, **kwargs)

# Update User model to include referral tracking
CustomUser.add_to_class('referred_by', models.ForeignKey(
    'self',
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name='referred_users'
))

# Signal to create ReferralReward when a deposit is approved
@receiver(post_save, sender=Deposit)
def create_referral_reward(sender, instance, **kwargs):
    # Check if a deposit was approved
    if instance.status == 'approved':
        try:
            # Find the referral record for the user who made the deposit
            referral = Referral.objects.get(invitee=instance.user)
            referrer = referral.inviter

            # Get or create the reward. This handles existing unpaid rewards.
            reward, created = ReferralReward.objects.get_or_create(
                referrer=referrer,
                referred=instance.user,
                defaults={
                    'deposit_amount': instance.amount,
                    'reward_amount': referral.bonus_amount,
                }
            )

            # If the reward has not been paid, credit the wallet and mark as paid.
            if not reward.is_paid:
                try:
                    wallet = referrer.wallet
                    wallet.balance += reward.reward_amount
                    wallet.save()

                    # Mark reward as paid and save
                    reward.is_paid = True
                    reward.save()

                    # Mark the referral as active
                    referral.status = 'active'
                    referral.save()

                except Wallet.DoesNotExist:
                    # This case should ideally not happen
                    pass

        except Referral.DoesNotExist:
            # The user was not referred, so no action is needed
            pass

class DailySpecial(models.Model):
    tier = models.ForeignKey(InvestmentTier, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    special_return_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)  # e.g., 1.5 for 50% extra returns
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tier.name} Special ({self.start_time.date()})"

    @property
    def special_return_amount(self):
        """Calculate the special return amount based on the multiplier"""
        return self.tier.return_amount * self.special_return_multiplier

    @property
    def is_currently_active(self):
        """Check if the special is currently active"""
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    class Meta:
        ordering = ['-start_time']

class Backup(models.Model):
    file_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    size = models.BigIntegerField(help_text="Size in bytes")
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('in_progress', 'In Progress')
        ],
        default='in_progress'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Backup'
        verbose_name_plural = 'Backups'

    def __str__(self):
        return f"{self.file_name} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"

    def size_display(self):
        """Return human-readable file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.size < 1024:
                return f"{self.size:.1f} {unit}"
            self.size /= 1024
        return f"{self.size:.1f} TB"

class AdminActivityLog(models.Model):
    """Model to track admin activities"""
    admin_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    target_model = models.CharField(max_length=100)
    target_id = models.IntegerField(null=True, blank=True)
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Admin Activity Log'
        verbose_name_plural = 'Admin Activity Logs'

    def __str__(self):
        return f"{self.admin_user.username} - {self.action} - {self.timestamp}"

class Voucher(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    voucher_image = models.ImageField(upload_to='vouchers/')
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.status}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            orig = Voucher.objects.get(pk=self.pk)
            if orig.status != 'approved' and self.status == 'approved':
                wallet, created = Wallet.objects.get_or_create(user=self.user)
                wallet.balance += self.amount
                wallet.save()
        super().save(*args, **kwargs)

class ChatUsage(models.Model):
    """Model to track chat usage for rate limiting"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Chat Usage'
        verbose_name_plural = 'Chat Usage'
    
    def __str__(self):
        return f"{self.user.username} - {self.timestamp}"
