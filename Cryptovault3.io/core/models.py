from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Deposit)
def create_referral_reward(sender, instance, created, **kwargs):
    # Check if a new deposit was approved
    if created and instance.status == 'approved':
        # Check if the user who made the deposit was referred by someone
        try:
            referral = Referral.objects.get(invitee=instance.user)
            # Check if a reward has already been given for this referral
            if not ReferralReward.objects.filter(referrer=referral.inviter, referred=instance.user).exists():
                # Create the reward
                ReferralReward.objects.create(
                    referrer=referral.inviter,
                    referred=instance.user,
                    deposit_amount=instance.amount,
                    reward_amount=referral.bonus_amount  # Use the bonus amount from the Referral model
                )
        except Referral.DoesNotExist:
            # The user was not referred, so no action is needed
            pass

# Update User model to include referral tracking
CustomUser.add_to_class(
    'referred_by',
    models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='referrals',
        null=True,
        blank=True
    )
) 