from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, AgentProfile, Address


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'agent_code', 'commission_percentage']
    search_fields = ['user__email', 'agent_code']
    ordering      = ['agent_code']


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display  = [
        'email', 'company_name', 'phone_number', 'gst_number',
        'is_verified_b2b', 'is_agent', 'assigned_agent', 'is_staff', 'date_joined',
    ]
    list_filter   = ['is_verified_b2b', 'is_agent', 'is_staff', 'is_active']
    search_fields = ['email', 'company_name', 'gst_number', 'phone_number']
    ordering      = ['-date_joined']

    fieldsets = UserAdmin.fieldsets + (
        ('B2B Details', {
            'fields': ('company_name', 'gst_number', 'phone_number', 'is_verified_b2b'),
        }),
        ('Agent', {
            'fields': ('is_agent', 'assigned_agent'),
            'description': 'Set is_agent=True for agent accounts. Use assigned_agent to map a buyer to their agent.',
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('B2B Details', {
            'fields': ('email', 'company_name', 'gst_number', 'phone_number', 'is_verified_b2b'),
        }),
        ('Agent', {
            'fields': ('is_agent', 'assigned_agent'),
        }),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display  = ['user', 'address_line_1', 'city', 'state', 'pincode', 'is_default_shipping', 'is_default_billing']
    list_filter   = ['state', 'is_default_shipping', 'is_default_billing']
    search_fields = ['user__email', 'city', 'pincode']