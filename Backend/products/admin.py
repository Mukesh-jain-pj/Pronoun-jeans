from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.text import slugify

from .models import Category, Product, ProductImage, ProductVariation, Color


def _unique_slug(base_slug):
    slug    = base_slug
    counter = 2
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def _unique_sku(base_sku):
    sku     = base_sku
    counter = 2
    while ProductVariation.objects.filter(sku=sku).exists():
        sku = f"{base_sku}-{counter}"
        counter += 1
    return sku


class ProductImageInline(admin.TabularInline):
    model   = ProductImage
    extra   = 0
    fields  = ['image', 'alt_text', 'order']
    ordering = ['order']


class ProductVariationInline(admin.TabularInline):
    model   = ProductVariation
    extra   = 0
    fields  = [
        'size', 'color_palette', 'color', 'sku',
        'b2b_price', 'per_piece_price', 'mrp', 'mrp_per_piece',
        'stock_quantity', 'image',
    ]
    readonly_fields = ['color']


@admin.action(description='Duplicate selected product(s)')
def clone_products(modeladmin, request, queryset):
    """
    Deep-clones each selected product:
      1. Clones the Product row with a new name + unique slug
      2. Clones all ProductVariation rows with new unique SKUs
      3. Clones all ProductImage rows
    Clone starts as inactive so admin can review before publishing.
    Single clone redirects to its edit page. Multiple clones stay on list.
    """
    original_pks = list(queryset.values_list('pk', flat=True))
    cloned_ids   = []

    for pk in original_pks:
        try:
            source = Product.objects.prefetch_related(
                'variations__color_palette', 'gallery_images'
            ).get(pk=pk)
        except Product.DoesNotExist:
            continue

        # 1. Clone Product
        new_name = f"{source.name} (Copy)"
        new_slug = _unique_slug(slugify(new_name))

        clone              = Product()
        clone.name         = new_name
        clone.slug         = new_slug
        clone.category     = source.category
        clone.description  = source.description
        clone.fabric_details = source.fabric_details
        clone.is_active    = False
        clone.moq          = source.moq
        clone.image        = source.image
        clone.save()

        # 2. Clone ProductVariations
        for v in source.variations.all():
            nv                  = ProductVariation()
            nv.product          = clone
            nv.size             = v.size
            nv.color            = v.color
            nv.color_palette    = v.color_palette
            nv.sku              = _unique_sku(f"{v.sku}-copy")
            nv.b2b_price        = v.b2b_price
            nv.per_piece_price  = v.per_piece_price
            nv.mrp              = v.mrp
            nv.mrp_per_piece    = v.mrp_per_piece
            nv.stock_quantity   = v.stock_quantity
            nv.image            = v.image
            nv.save()

        # 3. Clone ProductImages
        for img in source.gallery_images.all():
            ni          = ProductImage()
            ni.product  = clone
            ni.image    = img.image
            ni.alt_text = img.alt_text
            ni.order    = img.order
            ni.save()

        cloned_ids.append(clone.pk)

    count = len(cloned_ids)

    if count == 0:
        modeladmin.message_user(request, 'No products were cloned.', messages.WARNING)
        return

    if count == 1:
        edit_url = reverse('admin:products_product_change', args=[cloned_ids[0]])
        modeladmin.message_user(
            request,
            f'Product cloned (ID: {cloned_ids[0]}). Clone is inactive — review and publish when ready.',
            messages.SUCCESS,
        )
        return HttpResponseRedirect(edit_url)

    modeladmin.message_user(
        request,
        f'{count} products cloned (IDs: {", ".join(str(i) for i in cloned_ids)}). All clones start as inactive.',
        messages.SUCCESS,
    )


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display  = ['name', 'hex_code', 'swatch']
    search_fields = ['name']
    ordering      = ['name']

    def swatch(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<span style="display:inline-block;width:24px;height:24px;'
            'border-radius:50%;background:{};border:1px solid #ccc;"></span>',
            obj.hex_code,
        )
    swatch.short_description = 'Color'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display        = ['name', 'slug']
    search_fields       = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display  = ['product', 'alt_text', 'order']
    list_filter   = ['product']
    search_fields = ['product__name', 'alt_text']
    ordering      = ['product', 'order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display        = ['name', 'category', 'is_active', 'moq', 'created_at']
    list_filter         = ['is_active', 'category']
    search_fields       = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering            = ['-created_at']
    actions             = [clone_products]
    inlines             = [ProductImageInline, ProductVariationInline]

    fieldsets = (
        ('Product Info', {
            'fields': ('name', 'slug', 'category', 'description', 'fabric_details', 'is_active', 'moq'),
        }),
        ('Media', {
            'fields': ('image',),
        }),
    )


@admin.register(ProductVariation)
class ProductVariationAdmin(admin.ModelAdmin):
    list_display  = ['sku', 'product', 'size', 'color', 'b2b_price', 'per_piece_price', 'mrp', 'mrp_per_piece', 'stock_quantity']
    list_filter   = ['product__category', 'size']
    search_fields = ['sku', 'product__name', 'color']
    ordering      = ['product', 'size']