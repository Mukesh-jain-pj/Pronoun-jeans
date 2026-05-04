from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductVariation, Color


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display  = ['swatch', 'name', 'hex_code', 'variation_count']
    search_fields = ['name', 'hex_code']
    ordering      = ['name']

    def swatch(self, obj):
        return format_html(
            '<div style="width:28px;height:28px;border-radius:6px;'
            'background:{};border:1px solid #ccc;display:inline-block;'
            'vertical-align:middle;"></div>',
            obj.hex_code,
        )
    swatch.short_description = ''

    def variation_count(self, obj):
        return obj.variations.count()
    variation_count.short_description = 'Variations'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display        = ['name', 'slug', 'image']
    prepopulated_fields = {'slug': ('name',)}


class ProductVariationInline(admin.TabularInline):
    model  = ProductVariation
    extra  = 1
    fields = ['size', 'color', 'color_palette', 'sku', 'b2b_price', 'mrp', 'stock_quantity']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display        = ['name', 'category', 'is_active', 'created_at']
    list_filter         = ['is_active', 'category']
    prepopulated_fields = {'slug': ('name',)}
    inlines             = [ProductVariationInline]


@admin.register(ProductVariation)
class ProductVariationAdmin(admin.ModelAdmin):
    list_display  = ['swatch', 'product', 'size', 'color', 'color_palette', 'sku', 'b2b_price', 'stock_quantity']
    list_filter   = ['color_palette', 'product']
    search_fields = ['sku', 'product__name', 'color']

    def swatch(self, obj):
        hex_code = obj.color_palette.hex_code if obj.color_palette else '#CCCCCC'
        return format_html(
            '<div style="width:20px;height:20px;border-radius:50%;'
            'background:{};border:1px solid #ccc;display:inline-block;"></div>',
            hex_code,
        )
    swatch.short_description = ''

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'color_palette')