from rest_framework import serializers
from .models import Category, Product, ProductVariation


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['id', 'name', 'slug', 'image']


class ProductVariationSerializer(serializers.ModelSerializer):
    margin_percentage = serializers.SerializerMethodField()
    color_name        = serializers.SerializerMethodField()
    color_hex         = serializers.SerializerMethodField()

    class Meta:
        model  = ProductVariation
        fields = [
            'id', 'size', 'color', 'color_name', 'color_hex',
            'sku', 'b2b_price', 'mrp', 'margin_percentage', 'stock_quantity',
        ]

    def get_margin_percentage(self, obj):
        if not obj.mrp or obj.mrp == 0:
            return 0
        try:
            margin = ((obj.mrp - obj.b2b_price) / obj.mrp) * 100
            return round(float(margin), 1)
        except Exception:
            return 0

    def get_color_name(self, obj):
        """Return the structured color name if linked, else fall back to the plain string."""
        if obj.color_palette_id and 'color_palette' in obj.__dict__:
            return obj.__dict__['color_palette'].name
        return obj.color or ''

    def get_color_hex(self, obj):
        """Return the hex code if linked, else a neutral default."""
        if obj.color_palette_id and 'color_palette' in obj.__dict__:
            return obj.__dict__['color_palette'].hex_code
        return '#CCCCCC'


class ProductSerializer(serializers.ModelSerializer):
    variations    = ProductVariationSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'slug', 'description', 'fabric_details',
            'category', 'category_name', 'is_active', 'moq',
            'image', 'created_at', 'variations',
        ]