from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Commission
from products.models import ProductVariation
from accounts.serializers import AddressSerializer


class ProductVariationBriefSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    moq          = serializers.IntegerField(source='product.moq', read_only=True)

    class Meta:
        model  = ProductVariation
        fields = ['id', 'sku', 'size', 'color', 'b2b_price', 'stock_quantity', 'product_name', 'moq']


class CartItemSerializer(serializers.ModelSerializer):
    variation    = ProductVariationBriefSerializer(read_only=True)
    variation_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariation.objects.all(), source='variation', write_only=True
    )

    class Meta:
        model  = CartItem
        fields = ['id', 'variation', 'variation_id', 'quantity']

    def validate(self, data):
        variation = data.get('variation')
        quantity  = data.get('quantity')
        if quantity > 0 and quantity < variation.product.moq:
            raise serializers.ValidationError(
                f"Quantity must be 0 or >= MOQ ({variation.product.moq}) for this product."
            )
        return data


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    user  = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = Cart
        fields = ['id', 'user', 'items', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    variation = ProductVariationBriefSerializer(read_only=True)

    class Meta:
        model  = OrderItem
        fields = ['id', 'variation', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):
    items            = OrderItemSerializer(many=True, read_only=True)
    user             = serializers.StringRelatedField(read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    billing_address  = AddressSerializer(read_only=True)

    class Meta:
        model  = Order
        fields = [
            'id', 'user', 'status', 'payment_method', 'payment_status',
            'total_amount', 'shipping_address', 'billing_address',
            'items', 'created_at',
        ]


class CommissionSerializer(serializers.ModelSerializer):
    order_id      = serializers.IntegerField(source='order.id', read_only=True)
    order_total   = serializers.DecimalField(source='order.total_amount', max_digits=10, decimal_places=2, read_only=True)
    order_status  = serializers.CharField(source='order.status', read_only=True)
    order_date    = serializers.DateTimeField(source='order.created_at', read_only=True)
    buyer_email   = serializers.EmailField(source='order.user.email', read_only=True)
    buyer_company = serializers.CharField(source='order.user.company_name', read_only=True)
    agent_email   = serializers.EmailField(source='agent.email', read_only=True)

    class Meta:
        model  = Commission
        fields = [
            'id',
            'agent_email',
            'order_id', 'order_total', 'order_status', 'order_date',
            'buyer_email', 'buyer_company',
            'commission_percentage', 'amount',
            'status', 'created_at', 'paid_at',
        ]