import os
import django
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aicryptovault.settings')
django.setup()

from core.models import InvestmentTier

def create_tiers_like_screenshot():
    tiers = [
        {
            'name': 'Starter',
            'amount': Decimal('50.00'),
            'return_amount': Decimal('100.00'),
            'duration_days': 1,
            'min_level': 1,
            'description': 'Perfect for first-time investors. Quick 1-day return with 100% profit.'
        },
        {
            'name': 'Basic',
            'amount': Decimal('200.00'),
            'return_amount': Decimal('400.00'),
            'duration_days': 3,
            'min_level': 1,
            'description': 'Ideal for regular investors. 3-day investment with guaranteed returns.'
        },
        {
            'name': 'Standard',
            'amount': Decimal('500.00'),
            'return_amount': Decimal('1000.00'),
            'duration_days': 5,
            'min_level': 1,
            'description': 'Popular choice for steady growth. 5-day investment with substantial returns.'
        },
        {
            'name': 'Premium',
            'amount': Decimal('1000.00'),
            'return_amount': Decimal('2000.00'),
            'duration_days': 7,
            'min_level': 1,
            'description': 'For serious investors. 7-day investment with premium returns.'
        },
        {
            'name': 'Elite',
            'amount': Decimal('2000.00'),
            'return_amount': Decimal('4000.00'),
            'duration_days': 10,
            'min_level': 1,
            'description': 'High-value investment option. 10-day term with elite returns.'
        },
        {
            'name': 'Ultimate',
            'amount': Decimal('5000.00'),
            'return_amount': Decimal('10000.00'),
            'duration_days': 15,
            'min_level': 1,
            'description': 'Maximum returns for experienced investors. 15-day investment period.'
        },
    ]

    for tier in tiers:
        InvestmentTier.objects.update_or_create(
            name=tier['name'],
            defaults={
                'amount': tier['amount'],
                'return_amount': tier['return_amount'],
                'duration_days': tier['duration_days'],
                'min_level': tier['min_level'],
                'description': tier['description']
            }
        )

if __name__ == '__main__':
    print("Creating investment tiers to match screenshot...")
    create_tiers_like_screenshot()
    print("Investment tiers created successfully!") 