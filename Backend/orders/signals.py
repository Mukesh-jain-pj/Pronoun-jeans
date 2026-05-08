from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, Commission


@receiver(post_save, sender=Order)
def create_commission_on_delivered(sender, instance, created, **kwargs):
    """
    Feature 2: Commission is ONLY created/updated when an order reaches DELIVERED status.
    Never fires on order creation or any other status change.
    """
    if instance.status != Order.Status.DELIVERED:
        return

    buyer = instance.user
    agent = getattr(buyer, 'assigned_agent', None)
    if not agent:
        return

    try:
        agent_profile = agent.agent_profile
    except Exception:
        return

    commission_pct = agent_profile.commission_percentage
    if commission_pct <= 0:
        return

    base_amount = instance.grand_total
    amount      = (Decimal(str(commission_pct)) / Decimal('100')) * base_amount

    Commission.objects.get_or_create(
        order=instance,
        defaults={
            'agent':                 agent,
            'commission_percentage': commission_pct,
            'amount':                amount.quantize(Decimal('0.01')),
            'status':                Commission.Status.PENDING,
        },
    )

    # Feature 3: check bonus threshold after each delivered commission
    _check_and_award_bonus(agent, agent_profile)


def _check_and_award_bonus(agent, agent_profile):
    """
    Award a flat ₹5,000 bonus commission if total delivered sales >= ₹5,00,000
    and the bonus has not already been awarded.
    """
    from .models import Commission as C

    BONUS_THRESHOLD = Decimal(str(AgentProfile.BONUS_THRESHOLD))
    BONUS_AMOUNT    = Decimal(str(AgentProfile.BONUS_AMOUNT))

    # Import here to avoid circular import
    from accounts.models import AgentProfile

    # Already awarded?
    already_awarded = C.objects.filter(
        agent=agent,
        commission_percentage=Decimal('0.00'),
        amount=BONUS_AMOUNT,
    ).exists()
    if already_awarded:
        return

    # Sum all delivered sales for this agent
    from django.db.models import Sum
    total_delivered = (
        Order.objects.filter(
            user__assigned_agent=agent,
            status=Order.Status.DELIVERED,
        ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    )

    if total_delivered >= BONUS_THRESHOLD:
        C.objects.create(
            agent=agent,
            order=None,          # bonus is not tied to a specific order
            commission_percentage=Decimal('0.00'),
            amount=BONUS_AMOUNT,
            status=C.Status.PENDING,
        )