from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.db.models import Q
from .models import (
    CustomUser, InvestmentTier, Investment, Deposit, Withdrawal,
    Wallet, Referral, IPAddress, ReferralReward, DailySpecial,
    Backup, AdminActivityLog, Voucher, ChatUsage
)
from .banking_config import COMPANY_BANK_DETAILS, BANK_BRANCH_CODES
from datetime import datetime, timedelta

class MyAdminSite(AdminSite):
    pass

admin_site = MyAdminSite(name='myadmin')

# A simple ModelAdmin to display the models
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'level', 'is_staff', 'is_superuser')

class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'tier', 'amount', 'is_active', 'end_date')

class DepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'payment_method', 'status', 'created_at', 'display_proof', 'action_buttons')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('user__username', 'user__email', 'admin_notes')
    readonly_fields = ('created_at', 'updated_at', 'user', 'amount', 'payment_method', 'proof_image')
    actions = ['approve_selected_deposits', 'reject_selected_deposits', 'mark_for_review', 'bulk_verify_deposits']
    list_per_page = 25
    
    fieldsets = (
        ('Deposit Information', {
            'fields': ('user', 'amount', 'payment_method', 'status', 'created_at')
        }),
        ('Proof of Payment', {
            'fields': ('proof_image', 'display_proof_preview'),
            'classes': ('collapse',)
        }),
        ('Admin Review', {
            'fields': ('admin_notes', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_proof(self, obj):
        """Display proof image with enhanced view"""
        if obj.proof_image:
            return format_html(
                '<a href="{}" target="_blank" class="button">📄 View Proof</a>',
                obj.proof_image.url
            )
        return format_html('<span style="color: red;">❌ No proof uploaded</span>')
    display_proof.short_description = "Proof of Payment"
    
    def display_proof_preview(self, obj):
        """Enhanced proof preview in detail view"""
        if obj.proof_image:
            return format_html(
                '<div style="margin: 10px 0;">'
                '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ccc;" />'
                '<br><a href="{}" target="_blank" class="button">🔍 View Full Size</a>'
                '</div>',
                obj.proof_image.url, obj.proof_image.url
            )
        return "No proof image uploaded"
    display_proof_preview.short_description = "Proof Preview"
    
    def action_buttons(self, obj):
        """Quick action buttons for each deposit"""
        if obj.status == 'pending':
            return format_html(
                '<div style="white-space: nowrap;">'
                '<a href="{}" class="button" style="background: green; color: white; padding: 5px 10px; text-decoration: none; margin-right: 5px; border-radius: 3px;">✅ Approve</a>'
                '<a href="{}" class="button" style="background: red; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">❌ Reject</a>'
                '</div>',
                reverse('admin_approve_deposit', args=[obj.pk]),
                reverse('admin_reject_deposit', args=[obj.pk])
            )
        elif obj.status == 'approved':
            return format_html('<span style="color: green; font-weight: bold;">✅ Approved</span>')
        elif obj.status == 'rejected':
            return format_html('<span style="color: red; font-weight: bold;">❌ Rejected</span>')
        return ''
    action_buttons.short_description = "Actions"
    
    def approve_selected_deposits(self, request, queryset):
        """Bulk approve deposits with validation"""
        approved_count = 0
        failed_count = 0
        
        for deposit in queryset.filter(status='pending'):
            try:
                # Validate deposit before approval
                if not deposit.proof_image:
                    messages.warning(request, f'Deposit {deposit.id} has no proof image - skipping')
                    failed_count += 1
                    continue
                
                # Check if amount matches expected banking amounts
                if deposit.amount < 50:
                    messages.warning(request, f'Deposit {deposit.id} amount R{deposit.amount} is below minimum - review required')
                
                # Approve the deposit
                deposit.status = 'approved'
                deposit.admin_notes += f'\nApproved by {request.user.username} on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                deposit.save()
                approved_count += 1
                
                # Log admin activity
                AdminActivityLog.objects.create(
                    admin_user=request.user,
                    action='Approved Deposit',
                    target_model='Deposit',
                    target_id=deposit.id,
                    details=f'Approved deposit of R{deposit.amount} for user {deposit.user.username}'
                )
                
            except Exception as e:
                messages.error(request, f'Error approving deposit {deposit.id}: {str(e)}')
                failed_count += 1
        
        if approved_count > 0:
            messages.success(request, f'Successfully approved {approved_count} deposits.')
        if failed_count > 0:
            messages.error(request, f'Failed to approve {failed_count} deposits.')
        
        # Redirect back to the changelist
        return None
    
    approve_selected_deposits.short_description = "✅ Approve selected deposits"
    
    def reject_selected_deposits(self, request, queryset):
        """Bulk reject deposits"""
        rejected_count = 0
        for deposit in queryset.filter(status='pending'):
            deposit.status = 'rejected'
            deposit.admin_notes += f'\nRejected by {request.user.username} on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            deposit.save()
            rejected_count += 1
            
            # Log admin activity
            AdminActivityLog.objects.create(
                admin_user=request.user,
                action='Rejected Deposit',
                target_model='Deposit',
                target_id=deposit.id,
                details=f'Rejected deposit of R{deposit.amount} for user {deposit.user.username}'
            )
        
        messages.success(request, f'Successfully rejected {rejected_count} deposits.')
        
        # Redirect back to the changelist
        return None
    
    reject_selected_deposits.short_description = "❌ Reject selected deposits"
    
    def mark_for_review(self, request, queryset):
        """Mark deposits for manual review"""
        for deposit in queryset.filter(status='pending'):
            deposit.admin_notes += f'\nMarked for review by {request.user.username} on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            deposit.save()
        
        messages.info(request, f'Marked {queryset.count()} deposits for review.')
    
    mark_for_review.short_description = "🔍 Mark for review"
    
    def bulk_verify_deposits(self, request, queryset):
        """Bulk verify deposits against banking records"""
        verification_results = {
            'total': queryset.count(),
            'no_proof': 0,
            'below_minimum': 0,
            'suspicious': 0,
            'verified': 0
        }
        
        for deposit in queryset:
            # Check for missing proof
            if not deposit.proof_image:
                verification_results['no_proof'] += 1
                deposit.admin_notes += f'\n⚠️ No proof image - flagged by {request.user.username} on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                deposit.save()
                continue
            
            # Check for minimum amount
            if deposit.amount < 50:
                verification_results['below_minimum'] += 1
                deposit.admin_notes += f'\n⚠️ Below minimum amount R50 - flagged by {request.user.username} on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                deposit.save()
                continue
            
            # Check for suspicious patterns
            user_deposits = Deposit.objects.filter(user=deposit.user, created_at__gte=deposit.created_at - timedelta(hours=24))
            if user_deposits.count() > 3:
                verification_results['suspicious'] += 1
                deposit.admin_notes += f'\n⚠️ Multiple deposits in 24h - flagged by {request.user.username} on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                deposit.save()
                continue
            
            # Mark as verified
            verification_results['verified'] += 1
            deposit.admin_notes += f'\n✅ Verified by {request.user.username} on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            deposit.save()
        
        # Log admin activity
        AdminActivityLog.objects.create(
            admin_user=request.user,
            action='Bulk Verified Deposits',
            target_model='Deposit',
            target_id=None,
            details=f'Bulk verified {verification_results["total"]} deposits: {verification_results["verified"]} verified, {verification_results["no_proof"]} no proof, {verification_results["below_minimum"]} below minimum, {verification_results["suspicious"]} suspicious'
        )
        
        # Display results
        messages.info(request, 
            f'Verification complete: {verification_results["verified"]} verified, '
            f'{verification_results["no_proof"]} no proof, '
            f'{verification_results["below_minimum"]} below minimum, '
            f'{verification_results["suspicious"]} suspicious patterns'
        )
    
    bulk_verify_deposits.short_description = "🔍 Bulk verify deposits"
    
    def get_queryset(self, request):
        """Custom queryset with user information"""
        return super().get_queryset(request).select_related('user')
    
    def save_model(self, request, obj, form, change):
        """Override save to log admin activity"""
        if change and 'status' in form.changed_data:
            old_status = form.initial.get('status', 'unknown')
            new_status = obj.status
            
            AdminActivityLog.objects.create(
                admin_user=request.user,
                action=f'Changed Deposit Status',
                target_model='Deposit',
                target_id=obj.id,
                details=f'Changed status from {old_status} to {new_status} for deposit R{obj.amount}'
            )
        
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add custom JavaScript"""
        extra_context = extra_context or {}
        extra_context['custom_js'] = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Add action buttons to each row
            const rows = document.querySelectorAll('.results tbody tr');
            
            rows.forEach(function(row) {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 6) {
                    const statusCell = cells[2]; // Status column (adjust if needed)
                    const status = statusCell.textContent.trim();
                    const depositId = row.querySelector('input[type="checkbox"]')?.value;
                    
                    if (status === 'Pending' && depositId) {
                        // Create action buttons
                        const actionDiv = document.createElement('div');
                        actionDiv.style.cssText = 'display: inline-block; margin-left: 10px;';
                        actionDiv.innerHTML = `
                            <button onclick="approveDeposit(${depositId})" style="background: green; color: white; padding: 3px 8px; border: none; border-radius: 3px; margin-right: 5px; cursor: pointer;">✅ Approve</button>
                            <button onclick="rejectDeposit(${depositId})" style="background: red; color: white; padding: 3px 8px; border: none; border-radius: 3px; cursor: pointer;">❌ Reject</button>
                        `;
                        
                        // Add to the last cell
                        cells[5].appendChild(actionDiv);
                    }
                }
            });
        });
        
        function approveDeposit(depositId) {
            if (confirm('Are you sure you want to approve this deposit?')) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = window.location.href;
                
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrfmiddlewaretoken';
                csrfInput.value = document.querySelector('[name=csrfmiddlewaretoken]').value;
                
                const actionInput = document.createElement('input');
                actionInput.type = 'hidden';
                actionInput.name = 'action';
                actionInput.value = 'approve_selected_deposits';
                
                const indexInput = document.createElement('input');
                indexInput.type = 'hidden';
                indexInput.name = 'index';
                indexInput.value = '0';
                
                const selectInput = document.createElement('input');
                selectInput.type = 'hidden';
                selectInput.name = '_selected_action';
                selectInput.value = depositId;
                
                form.appendChild(csrfInput);
                form.appendChild(actionInput);
                form.appendChild(indexInput);
                form.appendChild(selectInput);
                
                document.body.appendChild(form);
                form.submit();
            }
        }
        
        function rejectDeposit(depositId) {
            if (confirm('Are you sure you want to reject this deposit?')) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = window.location.href;
                
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrfmiddlewaretoken';
                csrfInput.value = document.querySelector('[name=csrfmiddlewaretoken]').value;
                
                const actionInput = document.createElement('input');
                actionInput.type = 'hidden';
                actionInput.name = 'action';
                actionInput.value = 'reject_selected_deposits';
                
                const indexInput = document.createElement('input');
                indexInput.type = 'hidden';
                indexInput.name = 'index';
                indexInput.value = '0';
                
                const selectInput = document.createElement('input');
                selectInput.type = 'hidden';
                selectInput.name = '_selected_action';
                selectInput.value = depositId;
                
                form.appendChild(csrfInput);
                form.appendChild(actionInput);
                form.appendChild(indexInput);
                form.appendChild(selectInput);
                
                document.body.appendChild(form);
                form.submit();
            }
        }
        </script>
        """
        return super().changelist_view(request, extra_context)

class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')

class VoucherAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at', 'display_voucher')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__email')
    actions = ['approve_vouchers', 'reject_vouchers']

    def display_voucher(self, obj):
        if obj.voucher_image:
            return format_html('<a href="{}" target="_blank">View Voucher</a>', obj.voucher_image.url)
        return "No voucher"
    display_voucher.short_description = "Voucher Image"

    def approve_vouchers(self, request, queryset):
        for voucher in queryset:
            if voucher.status == 'pending':
                voucher.status = 'approved'
                voucher.save()
        self.message_user(request, f"{queryset.count()} vouchers were successfully approved.")
    approve_vouchers.short_description = "Approve selected vouchers"

    def reject_vouchers(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f"{queryset.count()} vouchers were rejected.")
    reject_vouchers.short_description = "Reject selected vouchers"

class ChatUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'timestamp')
    ordering = ('-timestamp',)
    
    def has_add_permission(self, request):
        return False  # Chat usage should only be created by the system
    
    def has_change_permission(self, request, obj=None):
        return False  # Chat usage records should not be modified

# Register models with the default Django admin site
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(InvestmentTier)
admin.site.register(Investment, InvestmentAdmin)
admin.site.register(Deposit, DepositAdmin)
admin.site.register(Withdrawal, WithdrawalAdmin)
admin.site.register(Wallet)
admin.site.register(Referral)
admin.site.register(IPAddress)
admin.site.register(ReferralReward)
admin.site.register(DailySpecial)
admin.site.register(Backup)
admin.site.register(AdminActivityLog)
admin.site.register(Voucher, VoucherAdmin)
admin.site.register(ChatUsage, ChatUsageAdmin)

# Also register with custom admin site for backward compatibility
admin_site.register(CustomUser, CustomUserAdmin)
admin_site.register(InvestmentTier)
admin_site.register(Investment, InvestmentAdmin)
admin_site.register(Deposit, DepositAdmin)
admin_site.register(Withdrawal, WithdrawalAdmin)
admin_site.register(Wallet)
admin_site.register(Referral)
admin_site.register(IPAddress)
admin_site.register(ReferralReward)
admin_site.register(DailySpecial)
admin_site.register(Backup)
admin_site.register(AdminActivityLog)
admin_site.register(Voucher, VoucherAdmin)
admin_site.register(ChatUsage, ChatUsageAdmin) 