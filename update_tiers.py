import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aicryptovault.settings')
django.setup()

from core.models import InvestmentTier

# Update tier descriptions
tier_updates = {
    'Starter': {
        'description': 'Perfect for first-time investors. Quick 1-day return with 100% profit.',
    },
    'Basic': {
        'description': 'Ideal for regular investors. 3-day investment with guaranteed returns.',
    },
    'Standard': {
        'description': 'Popular choice for steady growth. 5-day investment with substantial returns.',
    },
    'Premium': {
        'description': 'For serious investors. 7-day investment with premium returns.',
    },
    'Elite': {
        'description': 'High-value investment option. 10-day term with elite returns.',
    },
    'Ultimate': {
        'description': 'Maximum returns for experienced investors. 15-day investment period.',
    },
    'Platinum Plus': {
        'description': 'Exclusive tier for dedicated investors. 8-day investment with 200% profit.',
    }
}

# Update tiers
for name, data in tier_updates.items():
    tier = InvestmentTier.objects.get(name=name)
    tier.description = data['description']
    tier.save()

print("Tier descriptions updated successfully!") 