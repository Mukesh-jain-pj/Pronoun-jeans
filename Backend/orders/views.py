import logging
import razorpay
from decimal import Decimal, ROUND_HALF_UP
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Cart, CartItem, Order, OrderItem, Commission, SampleOrder, Coupon
from .tracking_service import get_bigship_tracking
from products.models import Product, ProductVariation
from accounts.models import Address, AgentPayment
from accounts.views import IsAgent
from .serializers import (
    CartSerializer, OrderSerializer, CommissionSerializer,
    SampleOrderSerializer, OrderTrackingUpdateSerializer, CouponSerializer,
)

logger = logging.getLogger(__name__)

SHIPPING_FEE            = Decimal('300.00')
FREE_SHIPPING_THRESHOLD = Decimal('15000.00')
Q2                      = Decimal('0.01')


def _r(value):
    return value.quantize(Q2, rounding=ROUND_HALF_UP)


def calc_gst_split(subtotal, coupon_pct=Decimal('0'), upi_pct=Decimal('0')):
    base         = _r(subtotal * Decimal('0.95'))
    gst          = _r(subtotal * Decimal('0.05'))
    coupon_disc  = _r(base * coupon_pct)
    upi_disc     = _r(base * upi_pct)
    total_disc   = _r(coupon_disc + upi_disc)
    disc_base    = _r(base - total_disc)
    pre_shipping = _r(disc_base + gst)
    shipping     = SHIPPING_FEE if pre_shipping < FREE_SHIPPING_THRESHOLD else Decimal('0.00')
    grand_total  = _r(pre_shipping + shipping)
    return {
        'base': base, 'gst': gst,
        'coupon_disc': coupon_disc, 'upi_disc': upi_disc,
        'total_disc': total_disc, 'disc_base': disc_base,
        'pre_shipping': pre_shipping, 'shipping': shipping,
        'grand_total': grand_total,
    }


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _resolve_address(address_id, user):
    if not address_id:
        return None
    try:
        return Address.objects.get(pk=address_id, user=user)
    except Address.DoesNotExist:
        return None


def _compute_subtotal(cart_items):
    return sum(
        Decimal(str(item.quantity)) * item.variation.b2b_price
        for item in cart_items
    )


def _resolve_coupon(coupon_code, subtotal):
    if not coupon_code:
        return None, Decimal('0')
    try:
        coupon = Coupon.objects.get(code=coupon_code.strip().upper())
        now    = timezone.now()
        if (coupon.is_active
                and coupon.valid_from <= now <= coupon.valid_to
                and subtotal >= coupon.min_order_value
                and coupon.discount_type == Coupon.DiscountType.PERCENTAGE):
            pct = Decimal(str(coupon.discount_value)) / Decimal('100')
            return coupon, pct
    except Coupon.DoesNotExist:
        pass
    return None, Decimal('0')


def _resolve_buyer(request, buyer_id=None):
    if request.user.is_agent and buyer_id:
        try:
            buyer = request.user.assigned_buyers.get(pk=buyer_id, is_verified_b2b=True)
        except Exception:
            return None, None, 'Buyer not found or not assigned to you.'
        if not buyer.agent_can_order:
            return None, None, 'This buyer has not granted you permission to place orders on their behalf.'
        return buyer, request.user, None
    return request.user, None, None


class CartDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)


class CartItemUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        product_id = request.data.get('product_id')
        items      = request.data.get('items', [])

        if not product_id or not items:
            return Response({'error': 'product_id and items are required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        total_quantity = sum(int(i.get('quantity', 0)) for i in items if int(i.get('quantity', 0)) > 0)
        if total_quantity == 0:
            return Response({'error': 'No valid quantities provided.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        if total_quantity < product.moq:
            return Response(
                {'error': f'Total quantity ({total_quantity}) must be >= MOQ ({product.moq}).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart, _ = Cart.objects.get_or_create(user=request.user)
        for item in items:
            qty = int(item.get('quantity', 0))
            if qty > 0:
                try:
                    variation = ProductVariation.objects.get(pk=item.get('variation_id'), product=product)
                    CartItem.objects.update_or_create(
                        cart=cart, variation=variation, defaults={'quantity': qty}
                    )
                except ProductVariation.DoesNotExist:
                    continue

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        try:
            item = CartItem.objects.select_related('cart').get(pk=pk, cart__user=request.user)
        except CartItem.DoesNotExist:
            return Response({'error': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)

        quantity = int(request.data.get('quantity', 1))
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()

        cart = Cart.objects.prefetch_related('items__variation').get(user=request.user)
        return Response(CartSerializer(cart).data)


class ActiveCouponsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = CouponSerializer

    def get_queryset(self):
        now = timezone.now()
        return Coupon.objects.filter(
            is_active=True, valid_from__lte=now, valid_to__gte=now,
        ).order_by('min_order_value')


class ApplyCouponView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        coupon_code = request.data.get('coupon_code', '').strip().upper()
        if not coupon_code:
            return Response({'error': 'Please enter a coupon code.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            coupon = Coupon.objects.get(code=coupon_code)
        except Coupon.DoesNotExist:
            return Response({'error': 'Invalid coupon code.'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        if not coupon.is_active:
            return Response({'error': 'This coupon is no longer active.'}, status=status.HTTP_400_BAD_REQUEST)
        if now < coupon.valid_from:
            return Response({'error': 'This coupon is not yet valid.'}, status=status.HTTP_400_BAD_REQUEST)
        if now > coupon.valid_to:
            return Response({'error': 'This coupon has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.prefetch_related('items__variation').get(user=request.user)
        except Cart.DoesNotExist:
            return Response({'error': 'Your cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = cart.items.all()
        if not cart_items.exists():
            return Response({'error': 'Your cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        subtotal = _compute_subtotal(cart_items)
        if subtotal < coupon.min_order_value:
            return Response(
                {'error': f'Minimum order value for this coupon is ₹{coupon.min_order_value}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        coupon_pct = Decimal(str(coupon.discount_value)) / Decimal('100')
        calc       = calc_gst_split(subtotal, coupon_pct=coupon_pct)

        return Response({
            'coupon_code':        coupon.code,
            'discount_type':      coupon.discount_type,
            'discount_value':     str(coupon.discount_value),
            'coupon_disc_amount': str(calc['coupon_disc']),
            'subtotal':           str(subtotal),
            'base':               str(calc['base']),
            'gst':                str(calc['gst']),
            'shipping':           str(calc['shipping']),
            'grand_total':        str(calc['grand_total']),
        })


class DirectUPICheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        payment_plan        = request.data.get('payment_plan', '').strip()
        utr_number          = request.data.get('utr_number', '').strip()
        shipping_address_id = request.data.get('shipping_address_id')
        billing_address_id  = request.data.get('billing_address_id')
        coupon_code         = request.data.get('coupon_code', '')
        buyer_id            = request.data.get('buyer_id')

        if payment_plan not in ('advance', 'full'):
            return Response({'error': "payment_plan must be 'advance' or 'full'."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not utr_number:
            return Response({'error': 'Please enter your UPI Transaction Reference ID (UTR).'},
                            status=status.HTTP_400_BAD_REQUEST)

        buyer, placed_by_agent, err = _resolve_buyer(request, buyer_id)
        if err:
            return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

        shipping_address = _resolve_address(shipping_address_id, buyer)
        billing_address  = _resolve_address(billing_address_id,  buyer)
        if not shipping_address:
            return Response({'error': 'Please select a shipping address.'}, status=status.HTTP_400_BAD_REQUEST)
        if not billing_address:
            return Response({'error': 'Please select a billing address.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.prefetch_related('items__variation__product').get(user=request.user)
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found.'}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = cart.items.all()
        if not cart_items.exists():
            return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        subtotal           = _compute_subtotal(cart_items)
        coupon, coupon_pct = _resolve_coupon(coupon_code, subtotal)
        upi_pct            = Decimal('0.01') if payment_plan == 'full' else Decimal('0')
        calc               = calc_gst_split(subtotal, coupon_pct=coupon_pct, upi_pct=upi_pct)
        grand_total        = calc['grand_total']
        pre_shipping       = calc['pre_shipping']
        shipping           = calc['shipping']

        if payment_plan == 'advance':
            amount_paid        = _r(pre_shipping * Decimal('0.10') + shipping)
            balance_due        = _r(pre_shipping - pre_shipping * Decimal('0.10'))
            payment_status_val = Order.PaymentStatus.PARTIAL
        else:
            amount_paid        = grand_total
            balance_due        = Decimal('0.00')
            payment_status_val = Order.PaymentStatus.PENDING

        order = Order.objects.create(
            user             = buyer,
            placed_by_agent  = placed_by_agent,
            shipping_address = shipping_address,
            billing_address  = billing_address,
            payment_method   = Order.PaymentMethod.DIRECT_UPI,
            payment_status   = payment_status_val,
            status           = Order.Status.PENDING_VERIFICATION,
            total_amount     = subtotal,
            coupon           = coupon,
            discount_amount  = calc['coupon_disc'],
            payment_plan     = payment_plan,
            upi_discount     = calc['upi_disc'],
            amount_paid      = amount_paid,
            balance_due      = balance_due,
            utr_number       = utr_number,
            payment_verified = False,
        )

        OrderItem.objects.bulk_create([
            OrderItem(order=order, variation=item.variation,
                      quantity=item.quantity, price=item.variation.b2b_price)
            for item in cart_items
        ])

        cart.items.all().delete()

        return Response({
            'order_id':    order.id,
            'grand_total': str(grand_total),
            'amount_paid': str(amount_paid),
            'balance_due': str(balance_due),
            'shipping':    str(shipping),
            'gst':         str(calc['gst']),
            'message':     'Order placed. Pending payment verification.',
        }, status=status.HTTP_201_CREATED)


class RazorpayCreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        shipping_address_id = request.data.get('shipping_address_id')
        billing_address_id  = request.data.get('billing_address_id')
        coupon_code         = request.data.get('coupon_code', '')
        buyer_id            = request.data.get('buyer_id')

        buyer, placed_by_agent, err = _resolve_buyer(request, buyer_id)
        if err:
            return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

        shipping_address = _resolve_address(shipping_address_id, buyer)
        billing_address  = _resolve_address(billing_address_id,  buyer)
        if not shipping_address:
            return Response({'error': 'Shipping address not found.'}, status=status.HTTP_400_BAD_REQUEST)
        if not billing_address:
            return Response({'error': 'Billing address not found.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.prefetch_related('items__variation__product').get(user=request.user)
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found.'}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = cart.items.all()
        if not cart_items.exists():
            return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        subtotal           = _compute_subtotal(cart_items)
        coupon, coupon_pct = _resolve_coupon(coupon_code, subtotal)
        calc               = calc_gst_split(subtotal, coupon_pct=coupon_pct)
        grand_total        = calc['grand_total']

        try:
            client         = get_razorpay_client()
            razorpay_order = client.order.create({
                'amount':          int(grand_total * 100),
                'currency':        'INR',
                'payment_capture': 1,
            })
        except Exception as e:
            return Response({'error': f'Failed to create Razorpay order: {str(e)}'},
                            status=status.HTTP_502_BAD_GATEWAY)

        django_order = Order.objects.create(
            user              = buyer,
            placed_by_agent   = placed_by_agent,
            shipping_address  = shipping_address,
            billing_address   = billing_address,
            payment_method    = Order.PaymentMethod.RAZORPAY,
            payment_status    = Order.PaymentStatus.PENDING,
            total_amount      = subtotal,
            coupon            = coupon,
            discount_amount   = calc['coupon_disc'],
            status            = Order.Status.PENDING,
            razorpay_order_id = razorpay_order['id'],
        )

        OrderItem.objects.bulk_create([
            OrderItem(order=django_order, variation=item.variation,
                      quantity=item.quantity, price=item.variation.b2b_price)
            for item in cart_items
        ])

        return Response({
            'razorpay_order_id': razorpay_order['id'],
            'amount':            int(grand_total * 100),
            'currency':          'INR',
            'key_id':            settings.RAZORPAY_KEY_ID,
            'django_order_id':   django_order.id,
            'name':              getattr(buyer, 'company_name', '') or buyer.email,
            'email':             buyer.email,
            'contact':           getattr(buyer, 'phone_number', '') or '',
        }, status=status.HTTP_201_CREATED)


class RazorpayVerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        razorpay_order_id   = request.data.get('razorpay_order_id', '')
        razorpay_payment_id = request.data.get('razorpay_payment_id', '')
        razorpay_signature  = request.data.get('razorpay_signature', '')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response({'error': 'All three Razorpay fields are required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            client = get_razorpay_client()
            client.utility.verify_payment_signature({
                'razorpay_order_id':   razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature':  razorpay_signature,
            })
        except razorpay.errors.SignatureVerificationError:
            return Response({'error': 'Payment signature verification failed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Verification error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        order.razorpay_payment_id = razorpay_payment_id
        order.razorpay_signature  = razorpay_signature
        order.payment_status      = Order.PaymentStatus.PAID
        order.status              = Order.Status.APPROVED
        order.save(update_fields=['razorpay_payment_id', 'razorpay_signature', 'payment_status', 'status'])

        try:
            Cart.objects.get(user=request.user).items.all().delete()
        except Cart.DoesNotExist:
            pass

        return Response({'message': 'Payment verified.', 'order_id': order.id})


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {'error': 'Use /api/orders/upi/checkout/ or /api/orders/razorpay/create/'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class OrderHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).prefetch_related('items__variation__product').order_by('-created_at')
        return Response(OrderSerializer(orders, many=True).data)


class AgentCommissionsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = CommissionSerializer

    def get_queryset(self):
        return Commission.objects.filter(
            agent=self.request.user
        ).select_related('order', 'order__user', 'agent').order_by('-created_at')


class AgentLedgerSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agent = request.user

        total_delivered_sales = (
            Order.objects.filter(
                user__assigned_agent=agent,
                status=Order.Status.DELIVERED,
            ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')
        )

        commission_qs    = Commission.objects.filter(agent=agent)
        total_commission = commission_qs.filter(
            order__isnull=False
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        bonus_earned = commission_qs.filter(
            order__isnull=True
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        total_earned = _r(Decimal(str(total_commission)) + Decimal(str(bonus_earned)))

        from accounts.models import AgentPayment
        total_paid_out = (
            AgentPayment.objects.filter(agent=agent).aggregate(t=Sum('amount'))['t']
            or Decimal('0.00')
        )

        outstanding_balance = _r(total_earned - Decimal(str(total_paid_out)))

        BONUS_THRESHOLD = Decimal('500000.00')
        BONUS_AMOUNT    = Decimal('5000.00')
        progress_pct    = min(float(total_delivered_sales / BONUS_THRESHOLD * 100), 100)
        bonus_unlocked  = total_delivered_sales >= BONUS_THRESHOLD

        return Response({
            'total_delivered_sales': str(_r(Decimal(str(total_delivered_sales)))),
            'total_commission':      str(_r(Decimal(str(total_commission)))),
            'bonus_earned':          str(_r(Decimal(str(bonus_earned)))),
            'total_earned':          str(total_earned),
            'total_paid_out':        str(_r(Decimal(str(total_paid_out)))),
            'outstanding_balance':   str(outstanding_balance),
            'bonus_threshold':       str(BONUS_THRESHOLD),
            'bonus_amount':          str(BONUS_AMOUNT),
            'bonus_progress_pct':    round(progress_pct, 1),
            'bonus_unlocked':        bonus_unlocked,
        })


class AgentEligibleBuyersView(APIView):
    permission_classes = [IsAgent]

    def get(self, request):
        buyers = request.user.assigned_buyers.filter(
            is_verified_b2b=True,
            agent_can_order=True,
        ).values('id', 'email', 'company_name', 'phone_number')
        return Response(list(buyers))


class AgentSampleOrdersListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = SampleOrderSerializer

    def get_queryset(self):
        return SampleOrder.objects.filter(
            agent=self.request.user
        ).select_related('buyer', 'agent').order_by('-date')

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user)


class AgentOrdersListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(
            user__assigned_agent=self.request.user
        ).select_related('user', 'shipping_address', 'billing_address').prefetch_related(
            'items__variation__product'
        ).order_by('-created_at')


class AgentOrderTrackingUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = OrderTrackingUpdateSerializer
    http_method_names  = ['patch']

    def get_queryset(self):
        return Order.objects.filter(user__assigned_agent=self.request.user)


class OrderTrackingTimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Order.objects.select_related('user', 'user__assigned_agent').get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        is_buyer = order.user == request.user
        is_agent = (
            order.user.assigned_agent is not None and
            order.user.assigned_agent == request.user
        )
        if not (is_buyer or is_agent):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        if not order.tracking_number:
            return Response({'timeline': [{
                'timestamp': None, 'status': 'Processing',
                'location': '', 'message': 'No tracking number assigned yet.',
            }]})

        logger.debug(
            f"[TRACKING] order={pk} awb='{order.tracking_number}' "
            f"user={request.user.id} is_agent={is_agent}"
        )

        try:
            timeline = get_bigship_tracking(order.tracking_number)
            logger.debug(f"[TRACKING] got {len(timeline)} events for order={pk}")
            return Response({'timeline': timeline})
        except Exception as e:
            logger.error(
                f"[TRACKING] BigShip call failed for order={pk} "
                f"awb='{order.tracking_number}': {type(e).__name__}: {e}"
            )
            return Response(
                {'error': 'Unable to fetch tracking details. Please try again later.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )