from rest_framework import serializers
from .models import Category, Product, ProductVariation, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['id', 'name', 'slug', 'image']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProductImage
        fields = ['id', 'image', 'alt_text', 'order']


class ProductVariationSerializer(serializers.ModelSerializer):
    set_price         = serializers.DecimalField(source='b2b_price', max_digits=10, decimal_places=2, read_only=True)
    margin_percentage = serializers.SerializerMethodField()
    color_name        = serializers.SerializerMethodField()
    color_hex         = serializers.SerializerMethodField()

    # Human-readable label, e.g. "L TO 3XL (Set)".
    # Useful if you ever want to render the display label in the frontend
    # rather than the raw key.
    size_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = ProductVariation
        fields = [
            'id', 'size', 'size_display', 'color', 'color_name', 'color_hex',
            'sku',
            'set_price',
            'b2b_price',
            'per_piece_price',
            'mrp',
            'mrp_per_piece',
            'margin_percentage',
            'set_breakdown',
            'stock_quantity', 'image',
        ]

    def validate_size(self, value):
        """
        Closes the API back door — even if someone bypasses the admin form
        and POSTs directly to the API, they cannot save an arbitrary string.
        """
        valid_keys = {choice[0] for choice in ProductVariation.SIZE_CHOICES}
        if value not in valid_keys:
            raise serializers.ValidationError(
                f"'{value}' is not a valid size. "
                f"Allowed values: {', '.join(sorted(valid_keys))}"
            )
        return value

    def get_size_display(self, obj):
        return obj.get_size_display()

    def get_margin_percentage(self, obj):
        try:
            if obj.per_piece_price and obj.mrp_per_piece and obj.mrp_per_piece > 0:
                margin = ((obj.mrp_per_piece - obj.per_piece_price) / obj.mrp_per_piece) * 100
            elif obj.mrp and obj.mrp > 0:
                margin = ((obj.mrp - obj.b2b_price) / obj.mrp) * 100
            else:
                return 0
            return round(float(margin), 1)
        except Exception:
            return 0

    def get_color_name(self, obj):
        if obj.color_palette:
            return obj.color_palette.name
        return obj.color or ''

    def get_color_hex(self, obj):
        if obj.color_palette:
            return obj.color_palette.hex_code
        return '#CCCCCC'


class ProductSerializer(serializers.ModelSerializer):
    variations     = ProductVariationSerializer(many=True, read_only=True)
    category_name  = serializers.CharField(source='category.name', read_only=True)
    gallery_images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'slug', 'description', 'fabric_details',
            'category', 'category_name', 'is_active', 'moq',
            'image', 'created_at', 'variations', 'gallery_images',
        ]