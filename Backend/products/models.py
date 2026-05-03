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


class ProductVariation(models.Model):
    product        = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variations")
    size           = models.CharField(max_length=50)
    color          = models.CharField(max_length=100)
    sku            = models.CharField(max_length=100, unique=True)
    b2b_price      = models.DecimalField(max_digits=10, decimal_places=2)
    mrp            = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "size", "color")
        verbose_name    = "Product Variation"

    def __str__(self):
        # Only access self.product if already loaded via select_related.
        # Never trigger a bare DB query from __str__.
        if 'product' in self.__dict__:
            product_name = self.__dict__['product'].name
        else:
            product_name = f"SKU {self.sku}"
        return f"{product_name} | {self.size} | {self.color}"