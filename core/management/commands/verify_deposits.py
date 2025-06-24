from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Deposit, CustomUser, AdminActivityLog
from core.banking_config import COMPANY_BANK_DETAILS
from datetime import datetime, timedelta
import csv
import os

class Command(BaseCommand):
    help = 'Verify deposits and generate reconciliation reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--status',
            type=str,
            choices=['pending', 'approved', 'rejected', 'all'],
            default='pending',
            help='Filter deposits by status'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back (default: 7)'
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export results to CSV file'
        )
        parser.add_argument(
            '--check-proofs',
            action='store_true',
            help='Check for deposits without proof images'
        )
        parser.add_argument(
            '--min-amount',
            type=float,
            default=50.0,
            help='Minimum amount threshold for verification'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Starting Deposit Verification Process...')
        )
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=options['days'])
        
        # Get deposits based on filters
        deposits = Deposit.objects.filter(created_at__range=(start_date, end_date))
        
        if options['status'] != 'all':
            deposits = deposits.filter(status=options['status'])
        
        self.stdout.write(f"📊 Analyzing {deposits.count()} deposits from {start_date.date()} to {end_date.date()}")
        
        # Statistics
        total_amount = sum(dep.amount for dep in deposits)
        pending_deposits = deposits.filter(status='pending')
        approved_deposits = deposits.filter(status='approved')
        rejected_deposits = deposits.filter(status='rejected')
        
        # Display statistics
        self.stdout.write("\n📈 DEPOSIT STATISTICS:")
        self.stdout.write(f"   Total Deposits: {deposits.count()}")
        self.stdout.write(f"   Total Amount: R{total_amount:,.2f}")
        self.stdout.write(f"   Pending: {pending_deposits.count()} (R{sum(dep.amount for dep in pending_deposits):,.2f})")
        self.stdout.write(f"   Approved: {approved_deposits.count()} (R{sum(dep.amount for dep in approved_deposits):,.2f})")
        self.stdout.write(f"   Rejected: {rejected_deposits.count()} (R{sum(dep.amount for dep in rejected_deposits):,.2f})")
        
        # Check for deposits without proof images
        if options['check_proofs']:
            self.check_missing_proofs(deposits)
        
        # Check for suspicious amounts
        self.check_suspicious_amounts(deposits, options['min_amount'])
        
        # Check for duplicate deposits
        self.check_duplicate_deposits(deposits)
        
        # Export to CSV if requested
        if options['export']:
            self.export_to_csv(deposits, start_date, end_date)
        
        # Generate banking reconciliation report
        self.generate_banking_report(deposits)
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Deposit verification completed!')
        )

    def check_missing_proofs(self, deposits):
        """Check for deposits without proof images"""
        deposits_without_proof = deposits.filter(proof_image='')
        
        if deposits_without_proof.exists():
            self.stdout.write(
                self.style.WARNING(f"\n⚠️  FOUND {deposits_without_proof.count()} DEPOSITS WITHOUT PROOF IMAGES:")
            )
            for deposit in deposits_without_proof:
                self.stdout.write(
                    f"   - ID: {deposit.id} | User: {deposit.user.username} | "
                    f"Amount: R{deposit.amount} | Status: {deposit.status} | "
                    f"Created: {deposit.created_at.strftime('%Y-%m-%d %H:%M')}"
                )
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ All deposits have proof images"))

    def check_suspicious_amounts(self, deposits, min_amount):
        """Check for deposits with suspicious amounts"""
        suspicious_deposits = deposits.filter(amount__lt=min_amount)
        
        if suspicious_deposits.exists():
            self.stdout.write(
                self.style.WARNING(f"\n⚠️  FOUND {suspicious_deposits.count()} DEPOSITS BELOW MINIMUM (R{min_amount}):")
            )
            for deposit in suspicious_deposits:
                self.stdout.write(
                    f"   - ID: {deposit.id} | User: {deposit.user.username} | "
                    f"Amount: R{deposit.amount} | Status: {deposit.status}"
                )

    def check_duplicate_deposits(self, deposits):
        """Check for potential duplicate deposits from same user"""
        user_deposits = {}
        duplicates = []
        
        for deposit in deposits:
            user_id = deposit.user.id
            if user_id not in user_deposits:
                user_deposits[user_id] = []
            user_deposits[user_id].append(deposit)
        
        for user_id, user_dep_list in user_deposits.items():
            if len(user_dep_list) > 1:
                # Check for deposits with same amount within 24 hours
                for i, dep1 in enumerate(user_dep_list):
                    for dep2 in user_dep_list[i+1:]:
                        if (dep1.amount == dep2.amount and 
                            abs((dep1.created_at - dep2.created_at).total_seconds()) < 86400):
                            duplicates.append((dep1, dep2))
        
        if duplicates:
            self.stdout.write(
                self.style.WARNING(f"\n⚠️  FOUND {len(duplicates)} POTENTIAL DUPLICATE DEPOSITS:")
            )
            for dep1, dep2 in duplicates:
                self.stdout.write(
                    f"   - User: {dep1.user.username} | Amount: R{dep1.amount} | "
                    f"Time difference: {abs((dep1.created_at - dep2.created_at).total_seconds()/3600):.1f} hours"
                )

    def export_to_csv(self, deposits, start_date, end_date):
        """Export deposits to CSV file"""
        filename = f"deposits_verification_{start_date.date()}_to_{end_date.date()}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'ID', 'Username', 'Email', 'Amount', 'Payment Method', 
                'Status', 'Has Proof', 'Created At', 'Admin Notes'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for deposit in deposits:
                writer.writerow({
                    'ID': deposit.id,
                    'Username': deposit.user.username,
                    'Email': deposit.user.email,
                    'Amount': deposit.amount,
                    'Payment Method': deposit.get_payment_method_display(),
                    'Status': deposit.get_status_display(),
                    'Has Proof': 'Yes' if deposit.proof_image else 'No',
                    'Created At': deposit.created_at.strftime('%Y-%m-%d %H:%M'),
                    'Admin Notes': deposit.admin_notes or ''
                })
        
        self.stdout.write(
            self.style.SUCCESS(f"\n📄 Exported {deposits.count()} deposits to {filename}")
        )

    def generate_banking_report(self, deposits):
        """Generate banking reconciliation report"""
        self.stdout.write("\n🏦 BANKING RECONCILIATION REPORT:")
        self.stdout.write(f"   Expected Account: {COMPANY_BANK_DETAILS['account_name']}")
        self.stdout.write(f"   Account Number: {COMPANY_BANK_DETAILS['account_number']}")
        self.stdout.write(f"   Bank: {COMPANY_BANK_DETAILS['bank_name']}")
        self.stdout.write(f"   Branch Code: {COMPANY_BANK_DETAILS['branch_code']}")
        
        # Payment method breakdown
        eft_deposits = deposits.filter(payment_method='eft')
        cash_deposits = deposits.filter(payment_method='cash')
        
        self.stdout.write(f"\n   EFT Deposits: {eft_deposits.count()} (R{sum(dep.amount for dep in eft_deposits):,.2f})")
        self.stdout.write(f"   Cash Deposits: {cash_deposits.count()} (R{sum(dep.amount for dep in cash_deposits):,.2f})")
        
        # Recent activity
        recent_activity = AdminActivityLog.objects.filter(
            target_model='Deposit',
            timestamp__range=(timezone.now() - timedelta(days=1), timezone.now())
        ).order_by('-timestamp')[:10]
        
        if recent_activity.exists():
            self.stdout.write("\n   Recent Admin Activity:")
            for activity in recent_activity:
                self.stdout.write(f"   - {activity.timestamp.strftime('%H:%M')}: {activity.action} by {activity.admin_user.username}") 