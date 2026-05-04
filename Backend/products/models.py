from django.db import models


class Category(models.Model):
    name  = models.CharField(max_length=255)
    slug  = models.SlugField(unique=True, max_length=255)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    category       = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    name           = models.CharField(max_length=255)
    slug           = models.SlugField(unique=True, max_length=255)
    description    = models.TextField(blank=True)
    fabric_details = models.TextField(blank=True, null=True)
    is_active      = models.BooleanField(default=True)
    moq            = models.PositiveIntegerField(default=10, help_text="Minimum Order Quantity for B2B clients")
    image          = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Color(models.Model):
    name     = models.CharField(max_length=100, unique=True)
    hex_code = models.CharField(max_length=7, default='#CCCCCC',
                                help_text='CSS hex color, e.g. #1A2B3C')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.hex_code})"


class ProductVariation(models.Model):
    product        = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variations")
    size           = models.CharField(max_length=50)

    # Legacy plain-text color — now auto-synced from color_palette on save.
    # blank=True, null=True so admins only need to pick the dropdown.
    color          = models.CharField(max_length=100, blank=True, null=True)

    # Structured color FK — the single source of truth going forward.
    color_palette  = models.ForeignKey(
        Color,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='variations',
    )

    sku            = models.CharField(max_length=100, unique=True)
    b2b_price      = models.DecimalField(max_digits=10, decimal_places=2)
    mrp            = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        # unique_together still enforces no duplicates when color is set
        unique_together = ("product", "size", "color")
        verbose_name    = "Product Variation"

    def save(self, *args, **kwargs):
        # Auto-sync the legacy color CharField from color_palette so
        # the fallback serializer field always has a value and
        # admins only need to fill in the dropdown.
        if self.color_palette_id:
            # Access name directly to avoid an extra query if already loaded
            if 'color_palette' in self.__dict__ and self.__dict__['color_palette']:
                self.color = self.__dict__['color_palette'].name
            else:
                # color_palette not prefetched — fetch name only
                self.color = Color.objects.filter(pk=self.color_palette_id).values_list('name', flat=True).first()
        super().save(*args, **kwargs)

    def __str__(self):
        if 'product' in self.__dict__:
            product_name = self.__dict__['product'].name
        else:
            product_name = f"SKU {self.sku}"
        color_label = self.color or (self.__dict__.get('color_palette') and self.__dict__['color_palette'].name) or '—'
        return f"{product_name} | {self.size} | {color_label}"