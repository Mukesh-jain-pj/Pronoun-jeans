from decimal import Decimal, ROUND_HALF_UP
from django.db import models


class Category(models.Model):
    name  = models.CharField(max_length=255)
    slug  = models.SlugField(unique=True, max_length=255)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class HeroSlide(models.Model):
    image     = models.ImageField(upload_to='hero_slides/')
    caption   = models.CharField(max_length=255, blank=True)
    order     = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering            = ['order', 'id']
        verbose_name        = 'Hero Slide'
        verbose_name_plural = 'Hero Slides'

    def __str__(self):
        return self.caption or f"Slide #{self.pk}"


class Product(models.Model):
    category       = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    name           = models.CharField(max_length=255)
    slug           = models.SlugField(unique=True, max_length=255)
    description    = models.TextField(blank=True)
    fabric_details = models.TextField(blank=True, null=True)
    is_active      = models.BooleanField(default=True)
    moq            = models.PositiveIntegerField(default=10)
    image          = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product  = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    image    = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=255, blank=True)
    order    = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Gallery image for {self.product.name} (#{self.pk})"


class Color(models.Model):
    name     = models.CharField(max_length=100, unique=True)
    hex_code = models.CharField(max_length=7, default='#CCCCCC')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.hex_code})"


class ProductVariation(models.Model):

    # ── Size choices ──────────────────────────────────────────────────────────
    # SOURCE OF TRUTH for sizes across admin, serializer, and any future form.
    # To add a new size: append a tuple here, then run makemigrations + migrate.
    # Stored value (left) = what goes in the DB and the API response.
    # Display label (right) = what the admin sees in the dropdown.
    #
    # AUDIT NOTE (2026-05-15): all existing rows confirmed clean.
    # Non-standard variants (3-XL, 4-XL, 2-XL, 4-XL TO 5-XL, 28-34, 30-36)
    # were normalized by fix_sizes_datamigration.py before this migration ran.
    SIZE_CHOICES = [
        # ── Standard apparel ──────────────────────────────────────────────────
        ('XS',            'XS — Extra Small'),
        ('S',             'S — Small'),
        ('M',             'M — Medium'),
        ('L',             'L — Large'),
        ('XL',            'XL — Extra Large'),
        ('XXL',           'XXL — Double XL'),
        ('3XL',           '3XL — Triple XL'),
        ('4XL',           '4XL — Four XL'),
        ('5XL',           '5XL — Five XL'),
        ('FS',            'FS — Free Size'),
        ('One Size',      'One Size'),

        # ── Numeric / waist sizes ─────────────────────────────────────────────
        ('28',            '28'),
        ('30',            '30'),
        ('32',            '32'),
        ('34',            '34'),
        ('36',            '36'),
        ('38',            '38'),
        ('40',            '40'),
        ('42',            '42'),
        ('44',            '44'),

        # ── Set / range sizes (alphabetical order for readability) ────────────
        # Apparel sets
        ('L TO 2XL',      'L TO 2XL (Set)'),
        ('L TO 3XL',      'L TO 3XL (Set)'),
        ('L TO 4XL',      'L TO 4XL (Set)'),
        ('L TO 5XL',      'L TO 5XL (Set)'),
        ('M TO 3XL',      'M TO 3XL (Set)'),
        ('M TO 4XL',      'M TO 4XL (Set)'),
        ('S TO XXL',      'S TO XXL (Set)'),
        ('4XL TO 5XL',    '4XL TO 5XL (Set)'),
        # Numeric sets
        ('28 TO 34',      '28 TO 34 (Set)'),
        ('28 TO 36',      '28 TO 36 (Set)'),
        ('30 TO 36',      '30 TO 36 (Set)'),
        ('30 TO 38',      '30 TO 38 (Set)'),
        ('32 TO 38',      '32 TO 38 (Set)'),
    ]

    product         = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variations")

    # max_length=20: longest stored value is '4XL TO 5XL' (10 chars).
    # Set to 20 for comfortable headroom.
    size            = models.CharField(
        max_length=20,
        choices=SIZE_CHOICES,
    )

    color           = models.CharField(max_length=100, blank=True, null=True)
    color_palette   = models.ForeignKey(
        Color, on_delete=models.SET_NULL, null=True, blank=True, related_name='variations'
    )
    sku             = models.CharField(max_length=100, unique=True)

    b2b_price       = models.DecimalField(max_digits=10, decimal_places=2)
    per_piece_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mrp             = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mrp_per_piece   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    set_breakdown   = models.CharField(
        max_length=255, blank=True, null=True,
        help_text='Size breakdown of the set, e.g. "1xL, 2xXL, 1x2XL, 1x3XL"',
    )

    stock_quantity  = models.PositiveIntegerField(default=0)
    image           = models.ImageField(upload_to='variations/', null=True, blank=True)

    class Meta:
        unique_together = ("product", "size", "color")
        verbose_name    = "Product Variation"

    def save(self, *args, **kwargs):
        for field in ('b2b_price', 'per_piece_price', 'mrp', 'mrp_per_piece'):
            val = getattr(self, field)
            if val is not None and not isinstance(val, Decimal):
                setattr(self, field,
                        Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        if self.color_palette_id:
            palette = self.__dict__.get('color_palette')
            if palette is not None:
                self.color = palette.name
            else:
                color_name = Color.objects.filter(
                    pk=self.color_palette_id
                ).values_list('name', flat=True).first()
                if color_name:
                    self.color = color_name

        super().save(*args, **kwargs)

    def __str__(self):
        product_name = (
            self.__dict__['product'].name
            if 'product' in self.__dict__
            else f"SKU {self.sku}"
        )
        return f"{product_name} | {self.size} | {self.color or '—'}"