from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, Commission


@receiver(post_save, sender=Order)
def create_commission_on_order(sender, instance, created, **kwargs):
    """
    Auto-create a Commission record when an order is placed,
    if the buyer has an assigned agent with an AgentProfile.
    Only triggers on new orders (created=True) to avoid duplicates.
    """
    if not created:
        return

    buyer = instance.user

    # Check if buyer has an assigned agent
    agent = getattr(buyer, 'assigned_agent', None)
    if not agent:
        return

    # Check agent has a profile with commission rate
    try:
        agent_profile = agent.agent_profile
    except Exception:
        return

    commission_pct = agent_profile.commission_percentage
    if commission_pct <= 0:
        return

    # Safety: avoid duplicate commissions
    if hasattr(instance, 'commission'):
        return

    amount = (Decimal(str(commission_pct)) / Decimal('100')) * instance.total_amount

    Commission.objects.get_or_create(
        order=instance,
        defaults={
            'agent':                 agent,
            'commission_percentage': commission_pct,
            'amount':                amount.quantize(Decimal('0.01')),
            'status':                Commission.Status.PENDING,
        },
    )